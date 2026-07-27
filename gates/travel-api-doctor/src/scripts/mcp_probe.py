#!/usr/bin/env python3
"""마이리얼트립 공개 MCP 엔드포인트 헬스 프로브.

https://mcp-servers.myrealtrip.com/mcp 에 JSON-RPC initialize와 tools/list를
보내 서버가 살아 있는지, 어떤 도구를 제공하는지 확인한다.
API 키가 필요 없다 (2026-07-03 기준 인증 없이 응답 확인).

사용법:
    python3 scripts/mcp_probe.py [--json] [--endpoint URL]

종료 코드: 정상 0, 실패 1.
"""

import argparse
import json
import sys
import urllib.request

DEFAULT_ENDPOINT = "https://mcp-servers.myrealtrip.com/mcp"
TIMEOUT_SECONDS = 10


def rpc(endpoint, method, params, request_id):
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = resp.read().decode("utf-8")
    # SSE 형식(data: {...}) 응답도 처리한다.
    if not raw.lstrip().startswith("{"):
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[len("data:"):].strip()
                break
    return json.loads(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args(argv)

    try:
        init = rpc(
            args.endpoint,
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "mrt-api-doctor", "version": "0.1.0"},
            },
            1,
        )
        server = init.get("result", {}).get("serverInfo", {})
        tools_resp = rpc(args.endpoint, "tools/list", {}, 2)
        tools = tools_resp.get("result", {}).get("tools", [])
    except Exception as exc:  # noqa: BLE001 - 프로브는 실패 사유를 그대로 보고한다
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"MCP 프로브 실패: {exc}")
            print(f"엔드포인트: {args.endpoint}")
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "endpoint": args.endpoint,
                    "server": server,
                    "toolCount": len(tools),
                    "tools": [t.get("name") for t in tools],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"MCP 서버 정상: {server.get('name', '?')} v{server.get('version', '?')}")
        print(f"엔드포인트: {args.endpoint}")
        print(f"도구 {len(tools)}종:")
        for t in tools:
            desc = (t.get("description") or "").split("\n")[0][:80]
            print(f"  - {t.get('name')}: {desc}")
    return 0 if tools else 1


if __name__ == "__main__":
    sys.exit(main())
