#!/usr/bin/env python3
"""개발자센터 공개 문서에서 규칙 인용문을 검증한다.

`rules/pitfalls.json`의 docQuote는 제출물의 근거다. 이 스크립트는
마이리얼트립 개발자센터 SPA의 현재 HTML을 읽고, HTML 안의 script 경로에서
`assets/index-*.js` 번들을 찾아 내려받은 뒤, 태그/엔티티/공백을 정규화해
각 docQuote가 문서 자료 안에 실제로 있는지 대조한다.

실제 API 키나 비공개 데이터는 필요하지 않다.
네트워크 실패는 exit 2, 인용문 누락은 exit 1, 모두 확인되면 exit 0이다.
"""

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_DOCS_HOME = "https://docs.myrealtrip.com/"
DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "pitfalls.json"
DEFAULT_TIMEOUT_SECONDS = 15
USER_AGENT = "mrt-api-doctor/0.1 public-doc-quote-verifier"

BLOCK_TAG_RE = re.compile(
    r"</?(?:article|aside|blockquote|br|dd|div|dl|dt|figcaption|figure|footer|h[1-6]|"
    r"header|hr|li|main|nav|ol|p|pre|section|table|tbody|td|tfoot|th|thead|tr|ul)"
    r"\b[^>]*>",
    re.IGNORECASE,
)
ANY_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_SRC_RE = re.compile(r"<script\b[^>]*\bsrc=[\"']([^\"']+\.js(?:\?[^\"']*)?)[\"']", re.IGNORECASE)


@dataclass(frozen=True)
class QuoteResult:
    rule_id: str
    title: str
    ok: bool
    doc_quote: str


def load_rules(path=DEFAULT_RULES_PATH):
    """규칙 JSON을 읽어 rules 배열을 반환한다."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"rules 배열을 찾을 수 없습니다: {path}")
    return rules


def decode_js_escapes(text):
    """JS 번들 문자열에서 자주 보이는 escape를 사람이 읽는 텍스트로 바꾼다."""

    def unicode_repl(match):
        return chr(int(match.group(1), 16))

    def hex_repl(match):
        return chr(int(match.group(1), 16))

    text = re.sub(r"\\u([0-9a-fA-F]{4})", unicode_repl, text)
    text = re.sub(r"\\x([0-9a-fA-F]{2})", hex_repl, text)
    replacements = {
        r"\/": "/",
        r"\n": " ",
        r"\r": " ",
        r"\t": " ",
        r"\"": '"',
        r"\'": "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def normalize_text(text):
    """HTML 태그, 엔티티, JS escape, 공백 차이를 제거해 인용문 대조용 텍스트를 만든다."""

    text = decode_js_escapes(text)
    text = html.unescape(text)
    text = BLOCK_TAG_RE.sub(" ", text)
    text = ANY_TAG_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("\u00a0", " ").replace("\ufeff", " ")
    return re.sub(r"\s+", " ", text).strip()


def discover_bundle_urls(home_html, home_url=DEFAULT_DOCS_HOME):
    """홈페이지 HTML에서 현재 배포의 JS 번들 URL을 찾는다."""

    script_srcs = [html.unescape(src) for src in SCRIPT_SRC_RE.findall(home_html)]
    index_srcs = [
        src for src in script_srcs
        if re.search(r"/assets/index-[^/]+\.js(?:\?|$)", src)
    ]
    candidates = index_srcs or [
        src for src in script_srcs
        if "/assets/" in src and urllib.parse.urlparse(src).path.endswith(".js")
    ]
    if not candidates:
        raise RuntimeError("개발자센터 HTML에서 JS 번들 script 경로를 찾지 못했습니다.")

    seen = set()
    urls = []
    for src in candidates:
        url = urllib.parse.urljoin(home_url, src)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def fetch_url(url, timeout=DEFAULT_TIMEOUT_SECONDS):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/javascript,text/javascript,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_public_document_text(home_url=DEFAULT_DOCS_HOME, timeout=DEFAULT_TIMEOUT_SECONDS):
    """개발자센터 홈 HTML과 현재 index 번들 텍스트를 내려받는다."""

    try:
        home_html = fetch_url(home_url, timeout=timeout)
        bundle_urls = discover_bundle_urls(home_html, home_url)
    except Exception as exc:  # noqa: BLE001 - CLI에서 정확히 보고한다
        raise RuntimeError(f"개발자센터 HTML 확인 실패: {home_url}: {exc}") from exc

    bundle_texts = []
    for url in bundle_urls:
        try:
            bundle_texts.append(fetch_url(url, timeout=timeout))
        except Exception as exc:  # noqa: BLE001 - 어떤 번들이 실패했는지 드러낸다
            raise RuntimeError(f"문서 번들 다운로드 실패: {url}: {exc}") from exc

    return "\n".join([home_html, *bundle_texts]), bundle_urls


def verify_quotes(rules, document_text):
    normalized_doc = normalize_text(document_text)
    results = []
    for rule in rules:
        quote = str(rule.get("docQuote", ""))
        normalized_quote = normalize_text(quote)
        results.append(
            QuoteResult(
                rule_id=str(rule.get("id", "<unknown>")),
                title=str(rule.get("title", "")),
                ok=bool(normalized_quote) and normalized_quote in normalized_doc,
                doc_quote=quote,
            )
        )
    return results


def render_text_report(results, source_label, bundle_urls):
    total = len(results)
    passed = sum(1 for result in results if result.ok)
    lines = [
        f"규칙 인용 검증: {passed}/{total}개 통과",
        f"문서 소스: {source_label}",
    ]
    if bundle_urls:
        lines.append("확인한 번들:")
        lines.extend(f"  - {url}" for url in bundle_urls)
    lines.append("")

    for result in results:
        marker = "OK" if result.ok else "FAIL"
        lines.append(f"[{marker}] {result.rule_id} — {result.title}")
        if not result.ok:
            lines.append(f"  누락 인용문: \"{result.doc_quote}\"")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="검증할 pitfalls.json 경로")
    parser.add_argument(
        "--document-text",
        help="네트워크 대신 사용할 로컬 문서 스냅샷/테스트 텍스트 경로",
    )
    parser.add_argument("--docs-home", default=DEFAULT_DOCS_HOME, help="개발자센터 홈 URL")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules)
        if args.document_text:
            source_label = str(args.document_text)
            bundle_urls = []
            document_text = Path(args.document_text).read_text(encoding="utf-8")
        else:
            source_label = args.docs_home
            document_text, bundle_urls = fetch_public_document_text(args.docs_home, args.timeout)
    except Exception as exc:  # noqa: BLE001 - 실패 원인을 숨기지 않는다
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"규칙 인용 검증을 실행할 수 없습니다: {exc}", file=sys.stderr)
        return 2

    results = verify_quotes(rules, document_text)
    ok = all(result.ok for result in results)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "source": source_label,
                    "bundleUrls": bundle_urls,
                    "results": [asdict(result) for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_text_report(results, source_label, bundle_urls))
        if not ok:
            print(
                "\n문서가 바뀌었거나 docQuote가 원문과 다릅니다. "
                "공개 문서를 다시 확인해 rules/pitfalls.json을 갱신하세요.",
                file=sys.stderr,
            )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
