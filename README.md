# AX Evidence Gates

공개 근거와 합성 데이터로 AI 결과물의 위험한 단정, 데이터 누락, 근거 부족을 점검하는 품질 게이트 3종입니다.

[![CI](https://github.com/ksungz/ax-evidence-gates/actions/workflows/ci.yml/badge.svg)](https://github.com/ksungz/ax-evidence-gates/actions/workflows/ci.yml)

이 저장소는 AX 인재전쟁 2026 예선 과제로 제작한 세 개의 독립 프로토타입을 공개 포트폴리오용으로 다시 정리한 것입니다. 기업 내부 데이터나 비공개 API를 사용하지 않으며, 공개 문서와 합성 샘플만으로 동작을 재현합니다.

## 한눈에 보기

| 품질 게이트 | 점검하는 문제 | 공개 도메인 | 자동 테스트 |
|---|---|---|---:|
| [Travel Booking Evidence Gate](gates/travel-booking/) | 예약 가능, 가격, 즉시 확정, 포함 사항 같은 구매 관련 문장에 근거가 있는지 확인 | 마이리얼트립 공개 TNA API 문서 | 9 |
| [Commerce Listing Preflight](gates/commerce-listing/) | 상품 속성, 태그, 사이즈, 상품정보제공고시 누락 신호를 등록 전에 확인 | 무신사 공개 문서와 국가법령정보센터 | 17 |
| [Investment Answer Gate](gates/investment-answer/) | 단정적 투자 권유, 수익 보장 표현, 사용자 조건과 위험 설명 누락을 확인 | 카카오페이증권 및 공공기관 공개 문서 | 7 |

총 33개 자동 테스트가 정상 입력, 위반 입력, 손상된 입력과 근거 누락을 검증합니다.

## 케이스 스터디

각 프로젝트에서 왜 생성 기능보다 검증 도구를 선택했는지, 어디까지 구현하고 무엇을 제외했는지 짧게 정리했습니다.

- [여행 예약 문장 근거 검수](docs/case-studies/travel-booking.md)
- [상품 등록 데이터 사전 점검](docs/case-studies/commerce-listing.md)
- [금융 안내 답변 안전성 점검](docs/case-studies/investment-answer.md)

## 왜 만들었나

AI가 자연스러운 답변이나 데이터를 빠르게 만들더라도, 실제 업무에 사용하려면 다음 질문에 답할 수 있어야 합니다.

- 어떤 공개 근거를 사용했는가?
- 확인하지 못한 내용은 무엇인가?
- 잘못된 입력이나 근거 부족을 어떻게 다루는가?
- AI가 제안한 결과를 사람이 어디에서 검토하는가?

세 프로젝트는 서로 다른 도메인을 다루지만 같은 원칙을 사용합니다.

1. 문제를 좁게 정의합니다.
2. 공개 자료로 확인할 수 있는 범위만 구현합니다.
3. 규칙 기반 검사를 반복 실행할 수 있게 만듭니다.
4. 각 finding에 입력 위치와 공개 근거를 연결합니다.
5. 확인할 수 없는 상태는 통과시키지 않고 사람의 검토 대상으로 남깁니다.

자세한 공통 구조는 [설계 문서](docs/architecture.md)에 정리했습니다.

## 실행

Python 3 표준 라이브러리만 사용합니다. 저장소 루트에서 전체 테스트를 실행할 수 있습니다.

```bash
./scripts/run-tests.sh
```

각 프로젝트의 데모 명령과 예제 입력은 해당 디렉터리의 README에서 확인할 수 있습니다.

## 대표 동작

### 여행 답변

```text
"2026년 5월 1일 예약 가능" -> 날짜와 옵션 근거가 있으면 SUPPORTED
"무료 취소 가능" -> 공개 필드에 취소 정책 근거가 없으면 BLOCKED
```

### 상품 등록 데이터

```text
"L 총장 71cm, XL 총장 68cm" -> SIZE-ORDER-INVERSION
"후드 티셔츠 + 스웨트셔츠 태그" -> TAG-MISMATCH-SWEATSHIRT
```

### 금융 안내 문구

```text
"지금 매수하세요. 수익이 확실합니다." -> 단정 권유와 수익 보장 위험
사용자 조건, 손실 가능성, 공개 근거가 없으면 추가 finding
```

## 저장소 구조

```text
.
├── gates/
│   ├── travel-booking/
│   ├── commerce-listing/
│   └── investment-answer/
├── docs/
│   ├── architecture.md
│   └── case-studies/
├── scripts/
│   └── run-tests.sh
└── .github/workflows/ci.yml
```

## 사용한 AI와 사람의 역할

AI는 공개 자료 탐색 보조, 후보 아이디어 비교, 코드와 테스트 초안, 문서 초안에 활용했습니다.

사람이 직접 결정하고 검증한 내용은 다음과 같습니다.

- 어떤 문제를 풀지와 구현 범위
- 사용할 근거와 제외할 근거
- 공식 기능처럼 오해될 표현 수정
- 공개 원문과 인용문의 일치 여부
- 정상, 위반, 손상 입력의 기대 결과
- 도구가 판단하지 못하는 한계

## 중요한 제한

- 세 도구는 각 기업의 공식 제품이 아닌 독립 프로토타입입니다.
- 기업 내부 시스템, 비공개 데이터, 계정, API 키를 사용하지 않습니다.
- 실제 예약, 상품 등록, 투자 판단 또는 준법 판정을 수행하지 않습니다.
- 규칙 기반 finding은 검토 신호이며 최종 판단을 대신하지 않습니다.
- 회사명과 상표는 공개 과제의 출처를 설명하기 위해서만 사용합니다.

자세한 고지는 [NOTICE.md](NOTICE.md)를 확인해 주세요.

## 관련 링크

- [상세 Case Study](https://ksungz-github-io.vercel.app/case-studies/ax-evidence-gates)
- [AX 인재전쟁 2026](https://hackathon.jocodingax.ai/)

## 라이선스

현재 별도의 오픈소스 라이선스를 부여하지 않았습니다. 이 저장소는 포트폴리오 검토와 실행 재현을 위해 공개되어 있습니다.
