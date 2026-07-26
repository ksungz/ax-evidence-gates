# Travel Booking Evidence Gate

## 문제

AI 여행 답변이 자연스러워도 "해당 날짜에 예약 가능", "즉시 확정", "최종 가격", "무료 취소"처럼 구매 결정에 영향을 주는 문장은 실제 상품 근거가 필요합니다.

## 사용자

여행 AI 답변을 만드는 개발자, PM과 QA 담당자가 출시 전 또는 응답 평가 단계에서 사용하도록 설계했습니다.

## 선택한 범위

추천 품질 전체를 평가하지 않고 예약 가능, 옵션 가격, 즉시 확정, 포함·불포함, 취소와 결제 완료처럼 사용자가 다시 확인해야 할 문장만 점검합니다.

마이리얼트립 공개 TNA API 문서에서 확인되는 endpoint와 field만 합성 fixture와 정책에 사용했습니다. 공개 문서에서 취소 정책 field를 확인하지 못했기 때문에 무료 취소 문장은 근거 부족으로 처리합니다.

## 구현

- 구조화된 answer contract
- 공개 field를 반영한 synthetic evidence fixture
- claim별 `SUPPORTED`, `CONDITIONAL`, `BLOCKED` 판정
- claim span과 JSON evidence path 반환
- Python 표준 라이브러리 기반 CLI와 테스트

## 검증

9개 테스트가 예약 근거 유무, 상대 날짜 기준일 누락, 대표가와 최종 가격 혼동, 취소 정책 근거 누락, 결제 완료 문구와 수량 초과를 확인합니다.

## 한계

실시간 재고, 가격, 예약, 결제와 취소를 조회하거나 수행하지 않습니다. 합성 데이터로 검증한 출시 전 QA 프로토타입입니다.

## 코드

[gates/travel-booking](../../gates/travel-booking/)
