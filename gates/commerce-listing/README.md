# listing-preflight

`listing-preflight`는 상품 등록 전(preflight)에 공개 기준으로 확인 가능한 누락·불일치 신호를 로컬에서 점검하는 Codex 플러그인 프로토타입입니다.

> Musinsa의 공식 제품이 아닌 독립 프로토타입입니다. 공개 문서와 합성 데이터만 사용합니다.

이 스키마는 무신사 어드민의 실제 등록 스키마 재현이 아니라, 공개 기준(상품정보제공고시·공개 상품 페이지 표시 항목·택소노미 글의 속성 서술)으로 선언한 검수용 포맷입니다.

무신사 내부 도구, 실제 어드민 연동, 비공개 API, 계정, API 키, 반려 사유 상세, 검색·추천 로직을 사용하지 않습니다.

## 문제 배경

공개 자료 기준으로 문제를 좁혔습니다.

- 무신사 기술블로그의 패션 택소노미 글은 2024년 무신사 서술 기준으로 주요 속성이 모두 기입된 의류 상품이 10% 미만이고, 태그 입력률은 약 70%이며, 후드 티셔츠에 `스웨트셔츠` 태그가 들어가는 사례 같은 오입력을 설명합니다: [패션 택소노미 구축기](https://techblog.musinsa.com/%EC%86%8D%EC%84%B1%EC%9D%84-%ED%99%9C%EC%9A%A9%ED%95%9C-%EC%B6%94%EC%B2%9C-%EA%B3%A0%EB%8F%84%ED%99%94-063ac9881801)
- 상품 등록의 어려움과 반려는 무신사 에듀 어드민 심화 교육의 공개 아카이브 문구와 커리큘럼 항목으로 확인했습니다: [Wayback 2025-02-13 스냅샷](http://web.archive.org/web/20250213032604/https://edu.musinsa.com/education/admin)
- 의류 상품 고시 항목은 국가법령정보센터의 전자상거래 등에서의 상품 등의 정보제공에 관한 고시 별표 (1) 의류 기준을 사용합니다: [law.go.kr](https://law.go.kr/%ED%96%89%EC%A0%95%EA%B7%9C%EC%B9%99/%EC%A0%84%EC%9E%90%EC%83%81%EA%B1%B0%EB%9E%98%EB%93%B1%EC%97%90%EC%84%9C%EC%9D%98%EC%83%81%ED%92%88%EB%93%B1%EC%9D%98%EC%A0%95%EB%B3%B4%EC%A0%9C%EA%B3%B5%EC%97%90%EA%B4%80%ED%95%9C%EA%B3%A0%EC%8B%9C)
- 공개 상품 페이지에서 `상품 고시 정보안내` 표와 판매자가 직접 등록한다는 문구를 관찰했습니다: [무신사 상품 6238769](https://www.musinsa.com/products/6238769)
- 상의 실측 검사는 무신사 뉴스룸이 공개한 총장·어깨너비·가슴 단면·소매 길이 항목으로 제한했습니다: [무신사 뉴스룸 2021-09-30](https://newsroom.musinsa.com/newsroom-menu/2021-0930-03)
- 2026년 무신사는 챗GPT 무신사 앱과 자체 `무신사 MCP` 기반 대화형 탐색을 공개했습니다: [무신사 뉴스룸 2026-06-09](https://newsroom.musinsa.com/newsroom-menu/2026-0609-01)

2024년 수치가 현재도 동일하다고 주장하지 않습니다. 이 프로젝트는 무신사가 공개적으로 확인한 문제의 원형을 바탕으로, 자연어·에이전트 기반 탐색의 비중이 커질수록 상품 속성·태그·고시 정보의 사전 검수 기준이 더 중요해진다는 관점에서 설계했습니다. 에이전트 커머스 관련 서사는 기능으로 구현하지 않고, 사실로 확인된 공개 자료와 가설을 분리합니다.

## 구성

```text
README.md
src/
  .codex-plugin/plugin.json
  preflight.py
  validate_report.py
  skills/listing-preflight/SKILL.md
  listing_preflight/
    engine.py
    input_schema.py
    rules.py
    judgment.py
    report_schema.py
    schema_validator.py
    sources.py
  schemas/report.schema.json
  examples/
    01-ok.json
    02-attr-gap.json
    03-tag-mismatch.json
    04-size-anomaly.json
    05-missing-disclosure.json
    expected-findings.json
  reports/
    01-ok.report.json
    02-attr-gap.report.json
    03-tag-mismatch.report.json
    04-size-anomaly.report.json
    05-missing-disclosure.report.json
  tests/
    test_examples.py
    test_input_errors.py
    test_report_schema.py
    test_rules.py
```

## Codex 플러그인으로 설치·실행

플러그인 루트는 `src/`입니다. Codex 앱이나 CLI에서 로컬 플러그인을 추가할 때 `src/`를 플러그인 루트로 지정합니다. 제작 과정에서는 로컬 marketplace metadata로 설치를 확인했지만, 해당 보조 파일은 공개 저장소에 포함하지 않았습니다.

설치 확인:

```bash
codex plugin list
```

목록에 `listing-preflight`가 `installed, enabled`로 표시되면 설치된 상태입니다.

설치 후 Codex에 아래 기본 문장을 입력하면 examples 5건 검수 데모가 재현됩니다.

```text
examples 5건으로 상품 등록 검수 데모 보여줘
```

이 기본 문장은 `src/examples/01-ok.json`부터 `src/examples/05-missing-disclosure.json`까지 리포트를 `src/reports/`에 재생성하고 `python3 src/validate_report.py src/reports/*.report.json`로 검증하는 흐름입니다.

## 3분 데모

아래 CLI 데모는 Python 표준 라이브러리만 사용하며, 외부 패키지·네트워크·API 키 없이 실행됩니다. Codex 앱에서 SKILL을 호출하려면 Codex CLI/앱의 기존 로그인 세션은 필요하지만, `listing-preflight` 플러그인 자체는 별도 API 키, 계정 정보, 비공개 데이터를 요구하지 않습니다.

```bash
python3 src/preflight.py \
  src/examples/01-ok.json \
  src/examples/02-attr-gap.json \
  src/examples/03-tag-mismatch.json \
  src/examples/04-size-anomaly.json \
  src/examples/05-missing-disclosure.json \
  --reports-dir src/reports

python3 src/validate_report.py src/reports/*.report.json
python3 -m unittest discover -s src/tests
```

예상 결과:

| 예제 | 목적 | 기대 finding |
|---|---|---|
| `01-ok.json` | 정상 | 0건 |
| `02-attr-gap.json` | 속성 누락 + 푸퍼 용어 클러스터 제안 | `TERM-CLUSTER-PUFFER`, `ATTR-GAP-LENGTH`, `ATTR-GAP-NECKLINE` |
| `03-tag-mismatch.json` | 후드티셔츠의 스웨트셔츠 태그 오입력 의심 | `TAG-MISMATCH-SWEATSHIRT` |
| `04-size-anomaly.json` | 단위 혼용 의심 + 사이즈 역전 | `SIZE-UNIT-SUSPECT`, `SIZE-ORDER-INVERSION` |
| `05-missing-disclosure.json` | 고시 항목 누락 | `GOSI-CLOTHING-07-MISSING` |

단일 파일만 볼 때:

```bash
python3 src/preflight.py src/examples/04-size-anomaly.json --out src/reports/04-size-anomaly.report.json
python3 src/validate_report.py src/reports/04-size-anomaly.report.json
```

## 구현 범위

- 결정적 룰 엔진: 필수 필드 누락, 의류 고시 9개 항목 존재, 제품 소재 백분율 표기, 상의 4개 실측 항목 결측·단위 혼용 의심·사이즈 간 역전값을 검사합니다.
- Codex 판단 레이어: `src/skills/listing-preflight/SKILL.md`에 상품명·상세설명·카테고리·태그 정합성 판단 지침을 둡니다. 로컬 데모 재현을 위해 `judgment.py`에 같은 6개 공개 사례 그룹만 보조 규칙으로 구현했습니다.
- strict JSON Schema 리포트: `src/schemas/report.schema.json`이 모든 finding의 입력 위치, 입력 인용, 공개 근거 URL, 근거 문구, diff 형식 수정안을 요구합니다.
- 예제 5건: `src/examples/expected-findings.json`과 자동 테스트가 finding 목록의 정확한 일치를 확인합니다.

## 한계

- 용어 사전은 무신사가 공개 문서화한 6개 사례 그룹으로 한정합니다. 동일 구조로 확장할 수 있지만, 이 프로젝트는 그 밖의 용어를 판단하지 않습니다.
- 사이즈 검증은 상의 4개 실측 항목(총장·어깨너비·가슴 단면·소매 길이)으로 한정합니다.
- 실제 무신사 어드민 스키마, 등록 반려 상세, 검색·추천·MCP 내부 동작을 재현하거나 추정하지 않습니다.
- 이미지 분석, 자동 상품 등록, 가격·재고·옵션 구조 검사는 포함하지 않습니다.
- `SIZE-UNIT-SUSPECT`는 공개 항목명과 데모용 참고 범위에 따른 검토 신호입니다. 실제 판정이나 변환을 대신하지 않습니다.

## 공개 문서 원칙

1. **스키마 선언**: "이 스키마는 무신사 어드민의 실제 등록 스키마 재현이 아니라, 공개 기준(상품정보제공고시·공개 상품 페이지 표시 항목·택소노미 글의 속성 서술)으로 선언한 검수용 포맷이다"를 README와 SKILL.md에 명시한다.
2. **연도 병기**: 택소노미 글(2024-07)의 수치(주요 속성 완비 10% 미만, 일 평균 신규 상품 3천 개, 태그 입력률 약 70% 등)는 반드시 "2024년 무신사 서술 기준"으로 인용하고, 현재도 동일하다고 단정하지 않는다.
3. **사실/가설 분리**: 에이전트 커머스 관련 서사는 출처 있는 사실 문장과 명시된 가설 문장을 구분해 표기한다.
4. **근거 인용 강제**: 모든 정량 주장에 출처 링크, 모든 검수 finding에 "입력의 어느 부분 + 어느 공개 기준" 근거 필드 (The Machine "근거 없는 점수는 점수가 아니다" 원칙의 설계 반영).
5. **커버리지 정직 고지**: 용어 사전은 무신사가 공개 문서화한 6개 사례 그룹으로 한정하며, 동일 구조로 확장 가능함을 밝힌다. 사이즈 검증은 상의 4개 실측 항목으로 한정한다.

## 공개 문서에서 피해야 할 표현

| 유형 | 예 (금지) | 대체 |
|---|---|---|
| 과장 | "반드시", "획기적", "유일한", "완벽하게 잡아낸다" | 검증된 범위를 그대로 서술 ("6개 사례 그룹에 대해") |
| 검증 불가 주장 | "속성이 빈 상품은 에이전트 커머스에서 존재하지 않는 상품", "무신사 MCP는 이렇게 검색한다" | 사실/가설 2단 문장 |
| 내부 도구 오해 표현 | 무신사 어드민 화면·반려 사유 상세를 아는 듯한 서술 | "공개 자료 기준" 한정, 반려는 교육 문구·커리큘럼 항목명까지만 |
| 어드민 스키마 재현 오해 | "무신사 등록 폼과 동일한 필드로 구성" | "공개 기준으로 선언한 검수용 포맷" (§2-1 문구) |
| 2024년 수치의 현재 단정 | "현재 속성 완비율은 10% 미만이다" | "2024년 무신사 서술 기준 10% 미만" (§2-2) |
| 기각된 수치 재유입 | "반품의 54%가 사이즈 때문" 등 검증되지 않은 외부 수치 | 인용하지 않음 |
| 표준형 단정 | "'패딩'이 무신사 표준 용어" | "동의어 클러스터 탐지 후 정규화 제안" |
