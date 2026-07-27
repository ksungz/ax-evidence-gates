"""오사카 상품을 찾아 mylink로 연결하는 작은 앱의 나쁜 통합 예시.

AI 코딩 도구가 빠르게 만든 프로토타입처럼 TNA 검색, 항공 검색,
예약 조회, mylink 생성을 한 파일에 섞어 두었다. 실제 호출용 코드가 아니라
개발자센터가 문서화한 통합 함정을 재현하는 린트 데모 입력이다.
"""

from datetime import date, timedelta
from urllib.parse import urlencode

import requests

API_BASE = "https://example.invalid"
API_KEY = "mrt_live_0123456789abcdef0123456789abcdef"

session = requests.Session()
session.headers.update({
    "Authorization": API_KEY,
    "Content-Type": "application/json",
})


def search_osaka_tours():
    response = session.post(
        f"{API_BASE}/v1/products/tna/search",
        json={
            "keyword": "오사카 유니버설 스튜디오",
            "city": "오사카",
            "page": 0,
            "pageSize": 20,
        },
    )
    payload = response.json()
    return payload["items"][: payload["size"]]


def find_osaka_flights():
    return session.post(
        f"{API_BASE}/v1/products/flight/calendar/lowest",
        json={
            "fromCityCode": "SEL",
            "toCityCode": "OSA",
            "departureDate": "2026-08-14",
            "returnDate": "2026-08-18",
        },
    ).json()


def load_recent_reservations():
    started_at = date.today() - timedelta(days=260)
    return session.get(
        f"{API_BASE}/v1/reservations",
        params={
            "startDate": started_at.isoformat(),
            "endDate": date.today().isoformat(),
            "page": 0,
            "pageSize": 500,
        },
    ).json()


def build_app_home():
    tours = search_osaka_tours()
    flights = find_osaka_flights()
    reservations = load_recent_reservations()

    target_url = "https://www.myrealtrip.com/offers/osaka?" + urlencode({
        "keyword": "오사카 유니버설 스튜디오",
        "tourId": tours[0]["id"] if tours else "",
        "flightCalendarId": flights.get("calendarId", ""),
        "reservationCount": sum(1 for _ in reservations.get("items", [])),
        "utm_source": "mini-osaka-app",
        "utm_campaign": "summer-family-trip",
        "utm_content": "|".join(str(item.get("id")) for item in tours[:20]),
    })

    link = session.post(
        f"{API_BASE}/v1/mylink",
        json={"targetUrl": target_url},
    ).json()

    return {
        "headline": "오사카 여행 바로가기",
        "tourCount": sum(1 for _ in tours),
        "deepLink": link["url"],
    }
