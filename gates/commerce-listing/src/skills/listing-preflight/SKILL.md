---
name: listing-preflight
description: Public-evidence listing preflight checks using synthetic product data. Use when reviewing a listing JSON with the repository's declared 검수용 포맷, deterministic rule engine, and evidence-limited term/tag judgment rules.
---

# listing-preflight

## 핵심 선언

이 스키마는 무신사 어드민의 실제 등록 스키마 재현이 아니라, 공개 기준(상품정보제공고시·공개 상품 페이지 표시 항목·택소노미 글의 속성 서술)으로 선언한 검수용 포맷이다.

이 스킬은 무신사 내부 도구가 아니다. 실제 무신사 어드민, 비공개 API, 계정, API 키, 심사 규칙, 검색·추천 로직에 접근하거나 이를 재현하지 않는다. 공개 자료로 확인 가능한 근거만 사용한다.

기본 데모 문장은 `examples 5건으로 상품 등록 검수 데모 보여줘`이다. 이 문장을 받으면 저장소 루트에서 `src/reports`를 데모 산출물로 재생성해도 된다. `src/examples/01-ok.json`부터 `src/examples/05-missing-disclosure.json`까지 리포트를 `src/reports`에 재생성하고 `src/validate_report.py src/reports/*.report.json`로 검증한다.

## 실행 절차

아래 명령은 저장소 루트에서 실행한다.

1. 입력 파일이 저장소의 검수용 JSON 포맷인지 확인한다.
2. 결정적 검사는 로컬 명령으로 실행한다.

```bash
python3 src/preflight.py src/examples/01-ok.json --out src/reports/01-ok.report.json
python3 src/validate_report.py src/reports/01-ok.report.json
```

3. Codex 판단 레이어가 필요한 경우 아래 6개 공개 사례 그룹 안에서만 판단한다.
4. 모든 finding에는 `rule_id`, `severity`, `input_location`, `input_quote`, `evidence.source_url`, `evidence.quote`, `suggestion.diff`를 채운다.
5. 근거 URL이나 근거 문구를 채울 수 없으면 finding을 만들지 말고 "공개 근거 부족"으로 남긴다.

## Codex 판단 범위

아래 6개 그룹만 사용한다. 표준형을 단정하지 않고, 클러스터 탐지와 검토 제안으로만 쓴다.

1. 푸퍼 자켓 / 패딩 / 패딩 점퍼
2. 크롭 / 숏
3. 퍼널넥 / 하이넥
4. U넥 / 라운드넥 혼재
5. '미디' 모호어: 용어 치환이 아니라 실측 수치 요구로 처리
6. 후드티셔츠 / 후드 / 후디 / 로고티 표기 변형, 그리고 후드 티셔츠에 '스웨트셔츠' 태그 오입력 탐지

판단 시에는 상품명·상세설명·카테고리·태그·속성 값을 대조한다. 공개 문서가 특정 표기를 무신사 표준형으로 지정하지 않았으므로 "정답 용어"라고 쓰지 않는다.

## 리포트 규칙

리포트는 `src/schemas/report.schema.json`을 통과해야 한다. 수정안은 각 finding의 `suggestion.diff`에 원본 대비 diff 형태로 적는다.

좋은 finding 예:

```json
{
  "rule_id": "TAG-MISMATCH-SWEATSHIRT",
  "severity": "warning",
  "input_location": "/tags",
  "input_quote": "스웨트셔츠",
  "evidence": {
    "basis_type": "musinsa_public_statement",
    "source_title": "무신사 기술블로그 - 패션 택소노미 구축기",
    "source_url": "https://techblog.musinsa.com/%EC%86%8D%EC%84%B1%EC%9D%84-%ED%99%9C%EC%9A%A9%ED%95%9C-%EC%B6%94%EC%B2%9C-%EA%B3%A0%EB%8F%84%ED%99%94-063ac9881801",
    "quote": "상품마다 선택해야 할 속성이 많고, 각 속성 클래스에 대한 가이드라인이 없어 서로 다른 해석으로 인한 오류가 많음"
  },
  "suggestion": {
    "action": "replace",
    "description": "후드티셔츠 상품의 스웨트셔츠 태그를 공개 오입력 사례 기준으로 검토한다.",
    "diff": "--- original\n+++ suggested\n@@\n- tags: 스웨트셔츠\n+ tags: 후드티셔츠 또는 후드 관련 태그 후보"
  }
}
```

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
| 검증 불가 주장 | "속성이 빈 상품은 에이전트 커머스에서 존재하지 않는 상품", "무신사 MCP는 이렇게 검색한다" | 사실과 가설을 구분한 2단 문장 |
| 내부 도구 오해 표현 | 무신사 어드민 화면·반려 사유 상세를 아는 듯한 서술 | "공개 자료 기준" 한정, 반려는 교육 문구·커리큘럼 항목명까지만 |
| 어드민 스키마 재현 오해 | "무신사 등록 폼과 동일한 필드로 구성" | "공개 기준으로 선언한 검수용 포맷" (§2-1 문구) |
| 2024년 수치의 현재 단정 | "현재 속성 완비율은 10% 미만이다" | "2024년 무신사 서술 기준 10% 미만" (§2-2) |
| 검증되지 않은 수치 | "반품의 54%가 사이즈 때문"처럼 공개 근거를 확인하지 못한 수치 | 인용하지 않음 |
| 표준형 단정 | "'패딩'이 무신사 표준 용어" | "동의어 클러스터 탐지 후 정규화 제안" |
