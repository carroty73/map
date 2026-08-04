# Phase 1 실험: 노션 DB에서 읽은 데이터를 브라우저에 그대로 출력만 한다.
# (지도, 스타일링, 카테고리 아이콘 등 UI는 넣지 않음 — 데이터 확인용)
#
# 노션 조회 관련 코드(fetch_all_pages, plain_title 등)는
# phase1_notion_read_cli.py와 완전히 동일하다 — 자세한 설명은 그 파일 주석 참고.
# 이 파일에서 새로 추가된 부분은 FastAPI로 웹서버를 띄우고, 결과를 HTML로
# 응답하는 부분뿐이다.
import os
from dotenv import load_dotenv
import requests
from fastapi import FastAPI  # 웹 서버(앱)를 만드는 프레임워크
from fastapi.responses import HTMLResponse  # 응답 형식이 HTML임을 명시하는 클래스

load_dotenv()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_COMPANY_DB_ID")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

app = FastAPI()  # 이 웹 서버 자체를 나타내는 객체. 라우트를 여기에 등록한다.


def fetch_all_pages(db_id):
    url = "https://" + "api.notion.com/v1/databases/" + db_id + "/query"
    results = []
    payload = {
        "page_size": 100,
        "filter": {
            "property": "숨김",
            "checkbox": {"equals": False},
        },
    }

    while True:
        res = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30).json()
        if "results" not in res:
            raise RuntimeError(f"노션 응답 오류: {res}")
        results.extend(res["results"])
        if not res.get("has_more"):
            break
        payload["start_cursor"] = res["next_cursor"]
    return results


def plain_title(prop):
    arr = (prop or {}).get("title") or []
    return arr[0]["plain_text"] if arr else ""


def plain_text(prop):
    arr = (prop or {}).get("rich_text") or []
    return arr[0]["plain_text"] if arr else ""


def select_name(prop, default="기타"):
    sel = (prop or {}).get("select")
    if not sel:
        return default
    return sel.get("name") or default


def number_or_none(prop):
    if not prop:
        return None
    return prop.get("number")


# @app.get("/") : 브라우저가 "/" (루트 경로)로 GET 요청을 보내면 이 함수를 실행
# response_class=HTMLResponse : 반환값을 JSON이 아니라 HTML로 응답하겠다는 표시
@app.get("/", response_class=HTMLResponse)
def index():
    pages = fetch_all_pages(NOTION_DB_ID)

    # 장소 하나당 <li> 한 줄짜리 HTML 문자열을 만들어서 이어 붙인다
    rows = ""
    for page in pages:
        props = page.get("properties") or {}
        rows += (
            "<li>"
            + plain_title(props.get("상호")) + " / "
            + plain_text(props.get("주소")) + " / "
            + select_name(props.get("카테고리")) + " / "
            + str(number_or_none(props.get("위도"))) + ", "
            + str(number_or_none(props.get("경도")))
            + "</li>"
        )

    # 제목(<h1>)만 있고 나머지는 꾸미지 않은 최소한의 HTML을 반환
    return f"""
    <html>
      <head><meta charset="utf-8"><title>노션 DB 읽기 테스트</title></head>
      <body>
        <h1>노션 DB 읽기 테스트</h1>
        <ul>{rows}</ul>
      </body>
    </html>
    """


# 이 파일을 직접 실행했을 때만(python phase1_notion_read_web.py) 동작
if __name__ == "__main__":
    import uvicorn  # FastAPI 앱을 실제로 실행시켜주는 서버 프로그램

    # host="0.0.0.0" : 모든 네트워크 주소에서 접속 허용
    # port=8001      : 8001번 포트에서 요청을 기다림(listen)
    uvicorn.run(app, host="0.0.0.0", port=8001)
