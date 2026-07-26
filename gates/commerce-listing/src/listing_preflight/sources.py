"""Public sources used by listing-preflight findings."""

TAXONOMY_URL = (
    "https://techblog.musinsa.com/"
    "%EC%86%8D%EC%84%B1%EC%9D%84-%ED%99%9C%EC%9A%A9%ED%95%9C-"
    "%EC%B6%94%EC%B2%9C-%EA%B3%A0%EB%8F%84%ED%99%94-063ac9881801"
)

GOSI_URL = "https://law.go.kr/행정규칙/전자상거래등에서의상품등의정보제공에관한고시"

GODO_GOSI_URL = "http://guide.godo.co.kr/guide/php/information.by.goods/information.by.goods.htm"

NEWSROOM_SIZE_URL = "https://newsroom.musinsa.com/newsroom-menu/2021-0930-03"

PUBLIC_PRODUCT_URL = "https://www.musinsa.com/products/6238769"

SOURCES = {
    "gosi_clothing": {
        "basis_type": "law",
        "source_title": "전자상거래 등에서의 상품 등의 정보제공에 관한 고시 별표 (1) 의류",
        "source_url": GOSI_URL,
        "quote": "제품 소재, 색상, 치수, 제조자, 제조국, 세탁방법 및 취급시 주의사항, 제조연월, 품질보증기준, A/S 책임자와 전화번호",
    },
    "gosi_material_percent": {
        "basis_type": "law",
        "source_title": "전자상거래 등에서의 상품 등의 정보제공에 관한 고시 별표 (1) 의류 - 제품 소재",
        "source_url": GOSI_URL,
        "quote": "섬유의 조성 또는 혼용률을 백분율로 표시",
        "supporting_sources": [
            {
                "source_title": "문구 대조용 정적 전재본 - godo 가이드",
                "source_url": GODO_GOSI_URL,
            }
        ],
    },
    "size_chart": {
        "basis_type": "musinsa_public_statement",
        "source_title": "무신사 뉴스룸 2021-09-30 실측 필터 소개",
        "source_url": NEWSROOM_SIZE_URL,
        "quote": "총장, 어깨너비, 가슴 단면, 소매 길이 등 실측을 숫자로 입력",
    },
    "taxonomy_terms": {
        "basis_type": "musinsa_public_statement",
        "source_title": "무신사 기술블로그 - 패션 택소노미 구축기",
        "source_url": TAXONOMY_URL,
        "quote": "상품마다 선택해야 할 속성이 많고, 각 속성 클래스에 대한 가이드라인이 없어 서로 다른 해석으로 인한 오류가 많음",
    },
    "public_product_disclosure": {
        "basis_type": "public_page_observation",
        "source_title": "무신사 공개 상품 페이지 상품 고시 정보안내",
        "source_url": PUBLIC_PRODUCT_URL,
        "quote": "공개 상품 페이지에서 상품 고시 정보안내 표와 판매자가 직접 등록한다는 문구를 확인했다.",
    },
}


def evidence(source_key):
    return dict(SOURCES[source_key])
