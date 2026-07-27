# Booking Evidence Gate for MyRealTrip TNA

> 이 디렉터리는 해커톤 준비 과정에서 만든 초기 여행 답변 검토 실험입니다. 최종 제출물은 [`MRT API Doctor`](../../gates/travel-api-doctor/)이며, 이 실험은 제출물 테스트 수와 대표 프로젝트 설명에 포함하지 않습니다.

`booking-evidence-gate`는 synthetic MyRealTrip TNA fixture의 field evidence를 기준으로 AI 여행 답변 안의 예약 관련 claim을 검수하는 Codex 플러그인 MVP입니다.

> MyRealTrip의 공식 제품이 아닌 독립 프로토타입입니다. 공개 문서와 합성 데이터만 사용합니다.

이 플러그인은 여행 추천 챗봇이 아닙니다. 이미 생성된 여행 답변이 충분한 근거 없이 구매 확신을 주는지 확인하는 출시 전 검수 레이어에 가깝습니다. 내부 MyRealTrip 데이터, 비공개 API, 기본 실행 경로의 API 키를 사용하지 않으며 실제 예약, 결제, 실시간 가격 조회를 수행하지 않습니다.

## 왜 Codex 플러그인인가

최종 형태는 여행자에게 직접 보이는 챗봇이 아니라, 여행 AI 응답 파이프라인 안이나 옆에서 동작하는 품질 게이트에 가깝습니다. 이 프로토타입에서는 내부 파이프라인, 비공개 데이터, 실서비스 API를 사용하지 않고 검수 로직을 synthetic sample data와 deterministic tests를 가진 Codex 플러그인으로 분리했습니다.

Codex는 이 프로토타입을 재현 가능한 검수 레이어로 보여주기에 적합합니다.

- 예약 가능 여부, 가격, 즉시확정, 포함사항, 취소 가능 여부처럼 구매 결정에 영향을 주는 문장에 필요한 근거 기준을 policy와 tests로 명시할 수 있습니다.
- AI 답변 문장이나 프롬프트가 바뀌어도 같은 audit 기준을 반복 실행할 수 있습니다.
- 검토자는 실제 서비스 API를 호출하지 않고도 sample answer, sample evidence fixture, local tests로 동작을 재현할 수 있습니다.
- 실제 서비스 환경에서는 같은 패턴을 AI response QA, prompt regression tests, pre-release review에 먼저 붙일 수 있습니다.
- 장기적으로 deterministic audit은 여행 AI 파이프라인의 pre-response review module로 확장할 수 있습니다.

보조 시각화 문서: [`docs/booking-evidence-gate-overview.html`](docs/booking-evidence-gate-overview.html)

## 공개 자료 근거

이 프로젝트는 공개 자료만 사용합니다.

- AX hackathon page: https://hackathon.jocodingax.ai/
- MyRealTrip AI travel conversation search blog: https://blog.myrealtrip.com/ai-travel-conversation-search/
- MyRealTrip Partner API documentation: https://docs.myrealtrip.com/
- MyRealTrip Partner API LLM text: https://docs.myrealtrip.com/llms-full.txt

MyRealTrip 블로그는 TNA 탐색과 예약 가능 여부 확인 흐름에서 category list, product search, product detail, option 또는 availability lookup tool을 연결하는 방식을 설명합니다. Partner API 문서에는 다음 TNA endpoint가 공개되어 있습니다.

- `POST /v1/products/tna/categories`
- `POST /v1/products/tna/search`
- `POST /v1/products/tna/detail`
- `POST /v1/products/tna/options`
- `POST /v1/products/tna/calendars`

## 사용한 공개 TNA Field

synthetic fixture와 policy는 공개 TNA 문서에서 확인되는 field만 사용합니다.

- Categories: `categories`, `categories[].name`, `categories[].value`, `totalCount`
- Search: `items`, `items[].gid`, `items[].itemName`, `items[].description`, `items[].salePrice`, `items[].priceDisplay`, `items[].category`, `items[].reviewScore`, `items[].reviewCount`, `items[].imageUrl`, `items[].productUrl`, `items[].deepLink`, `items[].tags`, `totalCount`, `page`, `perPage`, `hasNextPage`
- Detail: `gid`, `title`, `description`, `reviewScore`, `reviewCount`, `included`, `excluded`, `itineraries`, `itineraries[].title`, `itineraries[].description`
- Options: `selectedDate`, `options`, `options[].id`, `options[].name`, `options[].salePrice`, `options[].currency`, `options[].minPurchaseQuantity`, `options[].availablePurchaseQuantity`, `defaultOption`, `units`, `units[].id`, `units[].name`
- Calendars: `date`, `basePrice`, `blockDates`, `excludedOptionDates`, `instantConfirm`
- Common response wrapper: `data`, `meta`, `result`, `result.status`, `result.message`, `result.code`

여기서 사용한 공개 TNA 문서에는 cancellation-policy field가 없습니다. 따라서 "free cancellation" 같은 claim은 향후 공개 field나 tool trace가 추가되지 않는 한 이 MVP에서 blocked 처리됩니다.

## Gate가 검수하는 내용

gate는 structured answer contract를 읽고 각 claim을 검수합니다.

- Availability claim은 `POST /v1/products/tna/options`의 `selectedDate`가 일치하고 `options`가 비어 있지 않아야 합니다.
- Instant-confirmation claim은 `POST /v1/products/tna/calendars`의 `instantConfirm: true`가 필요합니다.
- Option price claim은 숫자형 `options[].salePrice`와 `options[].currency`가 필요합니다.
- Search result의 `items[].salePrice`, `priceDisplay`, calendar의 `basePrice`는 starting-price evidence로만 취급하며 final payment price evidence로 보지 않습니다.
- Included와 excluded claim은 product detail의 `included` 또는 `excluded`가 필요합니다.
- Relative date에는 `currentDate`가 필요합니다.
- Cancellation-policy claim은 이 MVP에서 사용하는 공개 TNA endpoint field에 cancellation-policy evidence가 없기 때문에 blocked 처리됩니다.
- Booking confirmed 또는 payment completed claim은 이 MVP가 booking이나 payment tool을 구현하지 않으므로 blocked 처리됩니다.

## 저장소 구조

```text
.
├── README.md
├── docs/booking-evidence-gate-overview.html
├── src/
│   ├── .codex-plugin/plugin.json
│   ├── skills/booking-evidence-gate/SKILL.md
│   ├── contracts/answer_contract.example.json
│   ├── contracts/try_in_chat_review.example.json
│   ├── examples/audit_summary.example.json
│   ├── examples/evidence_trace.example.json
│   ├── examples/mutation_examples.json
│   ├── examples/negative_examples.json
│   ├── examples/tool_trace.example.json
│   ├── fixtures/synthetic_tna_evidence.json
│   ├── policies/claim_policy.json
│   ├── scripts/mock_tna_adapter.py
│   ├── scripts/readiness_audit.py
│   └── tests/test_readiness_audit.py
```

플러그인 루트는 `src/`입니다. `docs/`에는 README에서 참조하는 보조 시각화 문서가 있습니다.

## 로컬 Codex 플러그인 확인

검증 과정에서는 local Codex CLI가 plugin root `src/`를 가리키도록 설정해 플러그인 등록, 설치와 skill loading을 확인했습니다. 로컬 환경에만 필요한 marketplace metadata는 공개 저장소에 포함하지 않았습니다.

별도 ephemeral Codex CLI session에서 설치된 skill을 호출해 `SKILL_OK booking-evidence-gate`를 반환하는 것도 확인했습니다. 또 다른 ephemeral CLI session에서는 설치된 skill에 `샘플 AI 여행 답변으로 검수 데모 보여줘`를 요청했고, 내장 Rapit ticket sample answer를 보여준 뒤 audit script를 실행해 supported claim은 `근거 있음`, unsupported free-cancellation claim은 `근거 부족`으로 표시하는 것을 확인했습니다.

이 확인은 local Codex CLI 기준의 marketplace registration, installation, skill loading, sample audit execution을 검증합니다. Codex Desktop app UI를 직접 열어 클릭 테스트했다는 뜻은 아닙니다.

## Try In Chat 프롬프트

Try In Chat의 default prompt는 Codex UI에서 보이도록 의도적으로 짧게 작성했습니다. 이 프롬프트는 추천 생성 흐름이 아니라 이미 생성된 AI 여행 답변을 출시 전 검수하는 흐름을 보여줍니다.

```text
샘플 AI 여행 답변으로 검수 데모 보여줘
```

사용자가 답변을 붙여넣지 않고 이 trigger만 보내면 `booking-evidence-gate` skill은 다음 내장 demo answer를 사용합니다.

```text
2026년 5월 1일 오사카 여행에서 간사이공항에서 난바로 이동한다면 라피트 편도 티켓을 추천합니다.
해당 날짜에 바로 예약 가능하고, 결제하면 즉시 확정됩니다.
성인 1명 기준 가격은 12,000원이며, 수하물 포함이고 무료 취소도 가능합니다.
```

예상되는 한국어 demo summary 형태:

- `근거 있음`: 2026-05-01 예약 가능, 즉시확정, 12,000원 옵션 가격, 수하물 포함
- `근거 부족`: 무료 취소 가능

free-cancellation claim은 이 MVP에서 사용하는 공개 TNA endpoint field에 cancellation-policy evidence가 없기 때문에 blocked 처리됩니다.

## 실행

repository root에서 실행합니다.

```bash
python3 src/scripts/readiness_audit.py \
  --answer src/contracts/answer_contract.example.json \
  --evidence src/fixtures/synthetic_tna_evidence.json \
  --policy src/policies/claim_policy.json
```

example contract의 예상 결과:

- `overall`: `PASS`
- 모든 example claim: `SUPPORTED`

Try In Chat style example을 실행하고 한국어 labels를 확인하려면 다음 명령을 사용합니다.

```bash
python3 src/scripts/readiness_audit.py \
  --answer src/contracts/try_in_chat_review.example.json \
  --evidence src/fixtures/synthetic_tna_evidence.json \
  --policy src/policies/claim_policy.json \
  --format korean-summary
```

## 테스트

```bash
python3 -m unittest discover -s src/tests -v
```

필수 MVP case:

- Evidence가 충분한 availability claim은 `SUPPORTED`입니다.
- Availability evidence가 없는 availability claim은 `BLOCKED`입니다.
- `currentDate` 없이 relative date를 확정하면 `BLOCKED`입니다.
- Search result starting price를 final payment price처럼 말하면 `BLOCKED`입니다.
- Cancellation-policy evidence 없는 cancellation claim은 `BLOCKED`입니다.

추가 확인 case:

- Booking confirmed 또는 payment completed 문구는 booking/payment tool trace가 없으면 hard `BLOCKED`입니다.
- 요청 수량이 `options[].availablePurchaseQuantity`를 초과하면 `BLOCKED`입니다.
- Verdict에는 claim span과 cited evidence paths가 포함됩니다.

## 선택 예시

- `src/scripts/mock_tna_adapter.py`는 live API를 호출하지 않고 fixture data를 endpoint group별로 반환합니다.
- `src/examples/tool_trace.example.json`은 synthetic TNA lookup trace를 보여줍니다.
- `src/examples/evidence_trace.example.json`은 JSON pointer evidence resolution을 보여줍니다.
- `src/examples/mutation_examples.json`은 negative mutations와 expected effects를 나열합니다.
- `src/examples/audit_summary.example.json`은 compact audit summary 예시입니다.

## 제한 사항

- fixture는 synthetic이며 live MyRealTrip inventory가 아닙니다.
- audit은 MyRealTrip API를 호출하지 않습니다.
- audit은 real-time inventory나 real-time prices를 표시하지 않습니다.
- audit은 booking, confirmation, cancellation, payment를 수행하지 않습니다.
- Cancellation-policy claim은 이 MVP에서 사용하는 공개 TNA endpoint field에 해당 evidence가 없기 때문에 의도적으로 blocked 처리됩니다.
- Companion-suitability claim은 documented fields가 suitability를 직접적으로 보여주지 않기 때문에 신중하게 처리됩니다.
