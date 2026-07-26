# KPS Decision Answer Gate

KPS Decision Answer Gate는 카카오페이증권 공개 자료를 바탕으로 샘플 상담/안내 답변 초안과 상담형 문구를 점검하는 로컬 품질 게이트입니다. 특정 종목을 추천하거나 수익을 예측하는 챗봇이 아니라, 상담/안내 답변 템플릿, 챗봇형·상담 지원 답변 fixture, FAQ/도움말, 앱 UX 문구를 배포하거나 업데이트하기 전에 필요한 확인 과정, 공개 근거, 위험과 한계 설명을 갖췄는지 검사합니다.

> 카카오페이증권의 공식 제품이 아닌 독립 프로토타입입니다. 공개 문서와 합성 데이터만 사용합니다.

검사 대상은 Markdown 또는 JSON fixture입니다. 실계좌, 실시간 시세, 비공개 고객 데이터, 카카오페이증권 내부 API는 사용하지 않습니다.

## 문제 배경

초보 투자자는 매수나 매도 전에 "손해 보지 않을까", "무엇을 확인해야 할까"라는 불안을 느낄 수 있습니다. 이 플러그인은 그 불안을 단정적인 매수/매도 결론으로 덮지 않고, 사용자 조건 확인, 공개 근거, 위험 설명, 다음 확인 행동으로 나누어 답변 초안을 검수합니다.

직접 사용자는 답변 생성, 상담 지원, QA, 개발 과정에서 답변 초안이나 fixture를 검수하는 담당자입니다. 이들은 상담/안내 답변 템플릿을 배포하기 전, FAQ/도움말과 앱 UX 문구를 업데이트하기 전, 챗봇형·상담 지원 답변 fixture를 회귀 테스트할 때 이 플러그인을 로컬 QA 도구로 사용할 수 있습니다. 최종 수혜자는 더 안전하고 납득 가능한 확인 과정을 받는 초보 투자자입니다.

## 공개 근거 URL

- E0 AX 인재전쟁 카카오페이증권 편: https://www.youtube.com/watch?v=aBuoojGjyf4
- E1 카카오페이증권 회사소개: https://www.kakaopaysec.com/company/about/dynamicPage.do
- E4 개인정보 처리 위탁 문서의 고객센터/AI 상담 업무 공개 항목: https://www.kakaopaysec.com/policy-detail/policy-002/dynamicPage.do
- E5 카카오페이 기술블로그 RAG/보안 가드레일 사례: https://tech.kakaopay.com/post/choonsiri/
- E6 주문장애 안내: https://www.kakaopaysec.com/portal/cstmnotice-obstc/dynamicPage.do
- E7 해외주식 시세 안내: https://www.kakaopaysec.com/guide/quotation/dynamicPage.do
- E8 해외주식 거래설명서: https://www.kakaopaysec.com/downloadFile.do?id=10427
- E9 해외주식 소수점 거래설명서: https://www.kakaopaysec.com/downloadFile.do?id=10361
- E13 금융소비자보호법 제17조/제19조 공개 기준: https://www.law.go.kr/LSW//lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0017&lsiSeq=277247&urlMode=lsScJoRltInfoR
- E14 금융투자협회 광고/컴플라이언스 공개 기준: https://law.kofia.or.kr/service/law/lawFullScreen.do?historySeq=1757&seq=136

이 근거들은 "공개 기준 기반 사전 품질 점검"의 참고자료입니다. 이 플러그인은 법률 판단, 투자 적합성 판정, 규제 준수 완료, 준법 완료를 주장하지 않습니다.

## 구성

- `src/.codex-plugin/plugin.json`: Codex 플러그인 메타데이터와 Try Chat 기본 프롬프트
- `src/skills/kps-decision-answer-gate/SKILL.md`: Codex가 로컬 검사기를 실행하고 결과를 설명하는 방법
- `src/kps_decision_answer_gate/gate.py`: Markdown/JSON 답변 검사 로직
- `src/scripts/kps_gate.py`: 로컬 CLI
- `src/examples/`: 재현 가능한 샘플 fixture
- `tests/test_kps_gate.py`: 표준 라이브러리 기반 자동 테스트

## 설치와 실행

별도 패키지 설치가 필요 없습니다. Python 3 표준 라이브러리만 사용합니다.

```bash
python3 src/scripts/kps_gate.py check src/examples/bad-answer.md --format markdown
```

JSON 출력이 필요하면 다음처럼 실행합니다.

```bash
python3 src/scripts/kps_gate.py check src/examples/bad-answer.md --format json
```

디렉터리 전체 fixture를 검사할 수도 있습니다.

```bash
python3 src/scripts/kps_gate.py check src/examples --format markdown
```

CI처럼 특정 심각도 이상에서 실패시키려면 `--fail-on`을 사용합니다.

```bash
python3 src/scripts/kps_gate.py check src/examples/bad-answer.md --fail-on high
```

## 3분 점검 흐름

1. 나쁜 답변 검사

```bash
python3 src/scripts/kps_gate.py check src/examples/bad-answer.md --format markdown
```

기대 결과: 단정 매수 표현, 수익 보장 오해 표현, 사용자 조건 누락, 위험 설명 누락, 공개 근거 URL 누락 finding이 표시됩니다.

2. 개선 답변 검사

```bash
python3 src/scripts/kps_gate.py check src/examples/better-answer.md --format markdown
```

기대 결과: 매수/매도 결론 없이 투자 목적, 기간, 보유 여부, 손실 감내 가능성, 손실 가능성, 시세/체결 불확실성, 공개 근거 URL이 포함되어 finding이 없습니다.

3. 상담형 fixture 검사

```bash
python3 src/scripts/kps_gate.py check src/examples/advisory-order-outage.md --format markdown
python3 src/scripts/kps_gate.py check src/examples/advisory-market-data-delay.md --format markdown
python3 src/scripts/kps_gate.py check src/examples/advisory-fractional-order.md --format markdown
```

기대 결과: 주문장애, 시세 지연, 소수점 주문 제한 각각의 공개 안내 기반 확인 항목 누락이 finding으로 표시됩니다.

4. 자동 테스트

```bash
python3 -m unittest discover -s tests
```

## finding 형식

모든 finding은 다음 필드를 포함합니다.

- `id`: 규칙과 위치를 식별하는 ID
- `severity`: `high`, `medium`, `low`, `info`
- `category`: 위험 표현, 사용자 조건, 근거 URL, 위험/한계 설명 등 범주
- `message`: 검수자가 읽을 설명
- `evidence_id`: 공개 근거 ID
- `evidence_url`: 공개 근거 URL
- `location`: 입력 파일의 위치 또는 섹션
- `suggestion`: 수정 또는 검토 제안
- `matched_text`: 탐지된 표현이 있을 때만 포함

## 하지 않는 것

- 특정 종목 추천
- 매수/매도 지시
- 수익률 예측
- 투자 적합성 판정
- 법률 판단 또는 준법 완료 판정
- 카카오페이증권 내부 상담 시스템 구현 주장
- 내부 API, 실계좌, 비공개 고객 데이터, 실시간 시세 사용

## 한계

이 플러그인은 공개 근거와 샘플 fixture를 기반으로 한 규칙 기반 검사기입니다. 실제 상담 품질, 법률 적합성, 금융상품 적합성, 실시간 시장 상황을 판정하지 않습니다. finding은 "검토 필요 신호"이며, 최종 답변 운영 전에는 담당자의 별도 검토가 필요합니다.

## 제출 이후 확장

AX 인재전쟁 제출 이후, finding을 사람이 확인하고 승인·수정·반려한 뒤 수정본을 다시 검사하는 LangGraph 워크플로우를 별도로 추가했습니다.

- [Investment Answer Review Workflow](../../workflows/investment-answer-review/)
- 이 확장 기능은 원래 제출물에 포함되지 않은 `v0.2 Post-hackathon iteration`입니다.

## 사용 대상과 검증 요약

### 무엇을, 누가, 어떤 상황에서 쓰나요?

KPS Decision Answer Gate는 상담/안내 답변 템플릿, 챗봇형·상담 지원 답변 fixture, FAQ/도움말, 앱 UX 문구를 배포하거나 업데이트하기 전에 단정 추천, 수익 보장, 근거 누락, 위험 설명 누락을 점검하는 로컬 Codex 플러그인입니다. 직접 사용자는 답변 생성, 상담 지원, QA, 개발 과정에서 금융 관련 문구를 검수하는 담당자입니다. 초보 투자자가 "지금 사도 되나", "손해 보지 않을까"처럼 매수·매도 전 불안을 가진 상황에서, 답변 초안이 결론을 대신 내려주거나 확인해야 할 조건을 빠뜨릴 수 있습니다. 이때 Markdown/JSON fixture를 플러그인에 넣어 공개 근거 URL, 사용자 조건, 위험·한계 설명, 다음 확인 행동이 갖춰졌는지 확인합니다.

### 왜 이 문제를 선택했나요?

카카오페이증권 영상은 초보 투자자가 매수·매도 앞에서 불안해하고, 정답 하나보다 사용자가 납득하고 안심할 수 있는 과정 설계가 중요하다고 말합니다. 증권 도메인에서는 근거 없는 "사도 됩니다", "수익이 확실합니다" 같은 문장이 고객에게 잘못된 확신을 줄 수 있습니다. 동시에 공식 문서에는 주문장애, 해외주식 시세 차이/지연, 소수점 주문 제한, 투자자 보호 관련 설명이 공개되어 있습니다. 그래서 추천 챗봇이 아니라, 상담/안내 답변 템플릿과 UX 문구가 공개 근거와 위험 설명을 갖췄는지 배포 전 반복 검수하는 로컬 QA 도구가 실제 문제에 더 안전하고 적합하다고 판단했습니다.

### 플러그인은 어떻게 작동하나요?

KPS Decision Answer Gate는 Markdown 또는 JSON 파일을 입력으로 받습니다. 먼저 답변 본문, `case_type`, `evidence` 필드를 읽고, 투자 판단형/주문장애/시세지연/소수점 주문 제한 같은 fixture 유형을 구분합니다. 그 다음 규칙 기반으로 직접 매수·매도 권유, 수익 보장·손실 축소 표현, 사용자 조건 누락, 공개 근거 URL 누락, 원금 손실·시세/체결 불확실성·주문 제한 설명 누락을 검사합니다. finding은 `severity`, `category`, `evidence_id`, `evidence_url`, `location`, `suggestion`을 포함해 Markdown/JSON으로 출력됩니다. 정보가 부족하면 답을 생성하지 않고 "검토 필요 신호"로 표시합니다.

### AI를 어떻게 활용했나요?

AI에는 영상/공개 자료 정리, 후보 아이디어 발산, 비판적 재검토, README/스킬 문구 초안, 테스트 케이스와 규칙 코드 구현 보조를 맡겼습니다. 직접 판단한 부분은 주제를 추천 챗봇이 아니라 품질 게이트로 좁힌 것, 직접 사용자를 일반 투자자가 아니라 답변 생성·상담 지원·QA·개발 담당자로 둔 것, 내부 데이터/실시간 시세 없이 샘플 fixture로 재현 가능하게 제한한 것입니다. 중간에 일부 표현이 확인되지 않은 공식 기능처럼 오해될 수 있다는 점을 의심했고, 최종 문서에서는 상담/안내 답변 초안으로 정리했습니다. 종목 추천, 투자 자문, 내부 시스템 구현처럼 보이는 제안은 받아들이지 않았습니다.

### 어떻게 검증했나요?

나쁜 예시 `bad-answer.md`에는 "지금 매수", "수익이 확실", "손실 가능성이 낮다" 같은 표현과 근거 누락을 넣었습니다. 실행 결과 high 6건, medium 2건이 나와 단정 추천, 수익 보장성 표현, 원금 손실 설명 부족, 공개 근거 URL 누락, 사용자 조건 누락을 잡는지 확인했습니다. 개선 예시 `better-answer.md`는 투자 목적, 기간, 보유 여부, 손실 감내 가능성, 원금 손실과 시세/체결 불확실성, 공개 URL을 포함해 finding 0건을 확인했습니다. 주문장애·시세지연·소수점 주문 제한 fixture도 각각 필요한 확인 항목 누락을 잡았습니다. `python3 -m unittest discover -s tests`는 8개 테스트 통과입니다. 한계는 규칙 기반 샘플 QA라 실제 상담 품질이나 법률 적합성을 판정하지 못한다는 점입니다.
