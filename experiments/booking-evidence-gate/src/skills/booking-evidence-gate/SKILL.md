---
name: booking-evidence-gate
description: Audit AI travel answers for MyRealTrip TNA booking-related claims and block unsupported claims about availability, prices, instant confirmation, inclusions, cancellations, reservation status, or companion suitability.
---

# Booking Evidence Gate

Use this skill when a user asks whether an AI travel answer is purchase-ready, booking-safe, or safe to show to end users.

This skill is not a travel recommender. It is a quality gate for booking-related claims.

## Evidence Boundary

Only use the public MyRealTrip Partner API TNA documentation and synthetic fixtures based on documented endpoints and fields:

- `POST /v1/products/tna/categories`
- `POST /v1/products/tna/search`
- `POST /v1/products/tna/detail`
- `POST /v1/products/tna/options`
- `POST /v1/products/tna/calendars`

Do not invent MyRealTrip field names. If a claim requires a field that is not present in the public TNA docs, mark the claim `BLOCKED` or `CONDITIONAL` instead of guessing.

## Quick Demo

When the user sends only "샘플 AI 여행 답변으로 검수 데모 보여줘" or asks for a sample AI travel-answer review demo without pasting an answer, do not ask for more input.

Treat this as a pre-release review demo for an already generated AI travel answer, not as a request to recommend a trip or look up live inventory.

First show this built-in sample answer:

```text
2026년 5월 1일 오사카 여행에서 간사이공항에서 난바로 이동한다면 라피트 편도 티켓을 추천합니다.
해당 날짜에 바로 예약 가능하고, 결제하면 즉시 확정됩니다.
성인 1명 기준 가격은 12,000원이며, 수하물 포함이고 무료 취소도 가능합니다.
```

Then audit it with `contracts/try_in_chat_review.example.json`, `fixtures/synthetic_tna_evidence.json`, and `policies/claim_policy.json`:

```bash
python3 scripts/readiness_audit.py \
  --answer contracts/try_in_chat_review.example.json \
  --evidence fixtures/synthetic_tna_evidence.json \
  --policy policies/claim_policy.json \
  --format korean-summary
```

Return the result in Korean with this shape:

```text
전체 판단: 수정 필요
근거 있음: 예약 가능, 즉시확정, 12,000원, 수하물 포함
근거 부족: 무료 취소 가능
이유: 제공된 근거 데이터에는 취소 정책 근거가 없습니다.
```

## Natural Paste Workflow

When the user pastes an AI travel answer in plain Korean, do not ask them for an answer contract first. Inspect the answer for purchase-impacting claims such as availability, price, instant confirmation, included items, cancellation wording, reservation status, and companion suitability.

For the built-in demo answer about the Osaka Rapit ticket on 2026-05-01, use `contracts/try_in_chat_review.example.json` with `fixtures/synthetic_tna_evidence.json` and `policies/claim_policy.json`, then summarize in Korean using:

- `근거 있음` for `SUPPORTED`
- `확인 필요` for `CONDITIONAL`
- `근거 부족` for `BLOCKED`

Recommended command from the plugin root:

```bash
python3 scripts/readiness_audit.py \
  --answer contracts/try_in_chat_review.example.json \
  --evidence fixtures/synthetic_tna_evidence.json \
  --policy policies/claim_policy.json \
  --format korean-summary
```

## Structured Audit Workflow

1. Ask for or locate a structured answer contract containing:
   - `currentDate` when the answer uses relative dates.
   - `claims[]` with `id`, `span`, `type`, and enough claim arguments such as `gid`, `selectedDate`, `optionId`, or `amount`.
   - `evidence[]` entries with JSON pointer paths into the provided evidence fixture.
2. Run the deterministic audit script from the plugin root:

```bash
python3 scripts/readiness_audit.py \
  --answer contracts/answer_contract.example.json \
  --evidence fixtures/synthetic_tna_evidence.json \
  --policy policies/claim_policy.json
```

3. Treat `BLOCKED` as release-blocking for purchase-readiness wording.
4. Treat `CONDITIONAL` as requiring softer language or a visible caveat.
5. Use `SUPPORTED` only when the claim's required field evidence is present and matches the claim arguments.

## Claim Handling

- Availability claims need `options` for the exact `selectedDate`; an empty `options` array does not support availability.
- Instant-confirmation claims need `instantConfirm: true` from `POST /v1/products/tna/calendars`.
- Final option price claims need numeric `options[].salePrice` from `POST /v1/products/tna/options`; `items[].salePrice`, `priceDisplay`, and `basePrice` are starting-price evidence only.
- Included or excluded item claims need `included` or `excluded` from `POST /v1/products/tna/detail`.
- Cancellation-policy claims are blocked in this MVP because the public TNA endpoints listed above do not expose a cancellation-policy field.
- Reservation confirmed, payment completed, or booking completed claims are blocked unless the system provides an implemented reservation or payment tool trace. This MVP does not implement those tools.
- Relative-date claims need `currentDate`; without it, do not finalize a date.
- Companion suitability claims such as "parents can do this comfortably" are blocked or conditional unless they are narrowly grounded in documented detail fields and phrased as a caveat, not a fact.

## Output

For user-facing review, answer in Korean with `근거 있음`, `확인 필요`, and `근거 부족`. Avoid exposing internal terms such as "answer contract", "fixture", "endpoint", or "field" unless the user asks for implementation details.

For developer-facing review, return the script's JSON result or summarize it with:

- Overall status: `PASS`, `CONDITIONAL`, or `FAIL`
- Counts by verdict
- Blocking claim spans
- Evidence paths used for supported claims
- Missing evidence paths for blocked claims
