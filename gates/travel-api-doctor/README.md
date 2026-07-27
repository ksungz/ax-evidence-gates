# MRT API Doctor

마이리얼트립 **마케팅파트너 Open API/MCP 통합 코드**를 작성하거나 리뷰하는 시점에 검수하는 Codex 플러그인입니다.

이 플러그인은 여행 추천 앱이 아닙니다. 상품 검색 결과를 대신 추천하거나 실제 예약 데이터를 조회하지 않고, 공개 개발자센터 문서가 설명한 통합 함정만 정적 검사와 근거 인용으로 보여주는 개발자 도구입니다.

## 왜 이 문제인가

마이리얼트립 영상의 중심 문제의식은 여행자가 상품을 탐색하고, 정보를 검증하고, 구매 확신에 이르기까지 겪는 피로입니다. 이 제출물은 그 문제를 직접 해결하는 앱이 아니라, 그 문제를 풀 앱과 에이전트를 만드는 외부 빌더가 마이리얼트립 여행 데이터를 안정적으로 연결하도록 돕는 기반 도구입니다.

마이리얼트립은 마케팅파트너 Open API와 MCP를 공개해 외부 빌더가 여행 상품 데이터를 자신의 제품에 연결할 수 있게 하고 있습니다. 공개 개발자센터 문서는 API 사용법과 함께 통합 시 주의해야 할 규약도 문서화합니다.

예를 들어 다음 함정은 모두 공개 문서에서 확인할 수 있습니다.

- 투어 검색은 page 1-based, 응답 필드는 `perPage`이고 숙소/항공 검색은 page 0-based, 응답 필드는 `size`입니다.
- 항공 파라미터 이름은 `fromCityCode`/`toCityCode`지만 실제 값은 도시코드가 아니라 공항코드입니다.
- `/v1/mylink`의 `targetUrl`이 너무 길면 문서화된 500 오류가 발생합니다.
- `/v1/reservations`에는 `pageSize` 최대값과 조회기간 제한이 있습니다.
- API별 rate limit, 429 응답, `X-RateLimit-Remaining` 헤더 확인이 문서화되어 있습니다.
- `Authorization: Bearer <API_KEY>` 형식에서 `Bearer` 누락은 문서가 설명한 흔한 401 원인입니다.

잘못된 페이지네이션, 공항코드/도시코드 혼동, 인증 오류, rate limit 미처리, mylink 오류는 개발 단계에서는 작은 통합 실수처럼 보이지만, 사용자 화면에서는 빈 결과, 잘못된 상품 연결, 끊긴 구매 흐름으로 이어질 수 있습니다. `mrt-api-doctor`는 빌더가 이런 함정을 에러 발생 뒤에 찾는 대신, 코드 작성·리뷰·CI 단계에서 먼저 볼 수 있게 합니다.

## 구성

1. **통합 린트** — `src/scripts/integration_lint.py`
   소스 코드(.py/.js/.ts 등)를 규칙 10종으로 정적 검사합니다. 모든 발견 항목에는 `rules/pitfalls.json`의 조치와 문서 원문 인용이 붙습니다.

2. **문서 근거 검증기** — `src/scripts/verify_rules.py`
   개발자센터 홈페이지 HTML에서 현재 `assets/index-*.js` 번들 경로를 파싱해 내려받고, HTML 태그·엔티티·공백을 정규화한 뒤 각 `docQuote`가 공개 문서 자료에 있는지 확인합니다. 실제 API 키는 필요하지 않습니다.

3. **MCP 프로브** — `src/scripts/mcp_probe.py`
   공개 MCP 엔드포인트에 JSON-RPC `initialize`와 `tools/list`를 보내 헬스와 도구 목록을 확인합니다. API 키 없이 실행됩니다.

4. **데모와 픽스처** — `src/examples/`, `src/fixtures/`
   나쁜/좋은 통합 예시와 합성 응답 샘플을 제공합니다. 픽스처는 실제 API 응답 저장본이 아니며, 전부 문서화된 필드와 규약만 보여주는 합성 데이터입니다.

## 실행

플러그인 루트는 `src/`입니다.

```bash
cd src

# 나쁜 통합 예시: 오사카 상품 앱 흐름에서 오류 4·경고 4·참고 1
python3 scripts/integration_lint.py examples/bad_integration.py

# 좋은 통합 예시: 발견 0건
python3 scripts/integration_lint.py examples/good_integration.py

# 자기 코드 검사
python3 scripts/integration_lint.py <파일|디렉터리> --format korean-summary

# 규칙 인용이 공개 개발자센터 문서 번들에 있는지 확인
python3 scripts/verify_rules.py

# 공개 MCP 엔드포인트 헬스체크
python3 scripts/mcp_probe.py

# 자동 테스트
python3 -m unittest discover -s tests -v
```

Python 3 표준 라이브러리만 사용합니다. 데모와 테스트에는 실제 API 키, 계정 정보, 비공개 데이터가 필요하지 않습니다.

## Codex에서 쓰기

스킬 `mrt-api-doctor`는 다음 상황에서 사용합니다.

- 마이리얼트립 Open API/MCP 통합 코드를 작성하거나 리뷰할 때
- "마이리얼트립 API 연동 코드 점검 데모 보여줘"처럼 키 없는 데모를 보고 싶을 때
- "왜 mylink가 500을 반환하지?", "왜 401이 나지?", "투어 검색 페이지가 왜 밀리지?" 같은 통합 오류 원인을 공개 문서 근거로 확인할 때
- MCP 엔드포인트 헬스와 도구 목록을 확인할 때

## 한계

- 휴리스틱 정적 검사라 미검출과 오검출이 있을 수 있습니다. 그래서 모든 발견 항목에 문서 원문 인용을 붙입니다.
- 실제 상품 검색, 예약 조회, 결제, 사용자 계정 데이터 접근은 하지 않습니다.
- `verify_rules.py`는 공개 문서가 바뀌면 실패할 수 있습니다. 이 경우 실패를 숨기지 않고 어떤 인용문이 문서에서 확인되지 않는지 보고합니다.
- 마이리얼트립과 무관한 독립 제출물이며, 공개 자료만 근거로 합니다.

## 공개 근거

- [마이리얼트립 개발자센터](https://docs.myrealtrip.com/) — API/MCP 사용 안내, 통합 규약, FAQ, rate limit, 인증 형식
- [마이리얼트립 기술블로그 OBA 위켄드톤 회고](https://blog.myrealtrip.com/yeoleo-dun-apiga-gyeolgwamulro-dolaogiggaji-mairieolteuribyi-oba-wikendeuton-hoego/) — Open API/MCP 공개 활용 사례
