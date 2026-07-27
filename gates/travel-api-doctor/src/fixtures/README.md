# Fixtures

이 폴더의 JSON은 **합성(synthetic) 샘플**이다. 실제 마이리얼트립 API 응답을 저장한 것이 아니다.

- 필드명과 규약(`perPage`/`size`, `page` 기준점, `airport.code` vs `city.code`, 에러 메시지 문구)은 개발자센터 docs.myrealtrip.com 문서에 근거한다 (2026-07-02 확인).
- 문서에 없는 응답 구조는 데모에 필요한 최소한으로만 구성했고, 실제 응답과 다를 수 있다.
- 용도: API 키 없이 페이지네이션 규약 차이와 에러 형태를 보여주는 로컬 데모.
