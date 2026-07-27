# 데모용 '좋은' 통합 코드 예시.
# 개발자센터가 문서화한 규약을 따른다. 실제로 실행하는 코드가 아니다.
import os
import time

import requests

API_KEY = os.environ["MRT_API_KEY"]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

MAX_RETRIES = 3  # 문서 권장: 429/500/503은 최대 3회 재시도


def post_with_retry(url, payload):
    for attempt in range(MAX_RETRIES):
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        return resp
    return resp


# 투어 검색: 1-based page, 응답 페이지 크기 필드는 perPage
tour_resp = post_with_retry(
    "https://example.invalid/v1/products/tna/search",
    {"keyword": "오사카 유니버설", "page": 1, "pageSize": 20},
)
per_page = tour_resp.json()["perPage"]

# 항공 캘린더: 공항 자동완성 응답의 airport.code(예: ICN)를 사용
flight_resp = post_with_retry(
    "https://example.invalid/v1/products/flight/calendar/lowest",
    {"fromCityCode": "ICN", "toCityCode": "NRT"},
)

# mylink: targetUrl 2,000자 제한을 호출 전에 검증
target_url = "https://www.myrealtrip.com/flights?from=ICN&to=NRT"
if len(target_url) > 2000:
    raise ValueError("mylink targetUrl은 2,000자 이하여야 합니다 (초과 시 500)")
mylink = post_with_retry(
    "https://example.invalid/v1/mylink",
    {"targetUrl": target_url},
)
