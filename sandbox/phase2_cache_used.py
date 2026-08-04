# Phase 2 실험: 노션 DB 조회 결과를 캐싱해서 얼마나 빨라지는지 확인한다.
#
# 노션 조회 관련 코드(fetch_all_pages, plain_title 등)는
# phase1_notion_read_cli.py와 동일하다 — 자세한 설명은 그 파일 주석 참고.
# 이 파일에서 새로 추가된 부분은 "캐시(cache)" 개념뿐이다.
import os
import time
from dotenv import load_dotenv
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

load_dotenv()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_COMPANY_DB_ID")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

app = FastAPI()

# 캐시: 조회한 노션 데이터를 담아두는 "그냥 파이썬 변수".
# 서버가 켜져 있는 동안 메모리에 남아있고, 요청이 올 때마다 노션을 다시
# 부르는 대신 이 값을 그대로 돌려준다.
cache = {
    "pages": None,       # 마지막으로 조회한 결과 (아직 없으면 None)
    "cached_at": None,   # 마지막으로 캐시를 채운 시각
}


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


def unique_id_str(prop):
    """고유번호(unique_id) 타입 속성을 "접두어+번호" 문자열로 만든다. (예: UID-1000)"""
    uid = (prop or {}).get("unique_id")
    if not uid:
        return ""
    return f"{uid.get('prefix') or ''}{uid.get('number')}"


def get_pages(force_refresh=False):
    """캐시에 데이터가 있으면 그걸 쓰고, 없거나 강제 갱신이면 노션을 다시 조회한다."""
    if cache["pages"] is None or force_refresh:
        cache["pages"] = fetch_all_pages(NOTION_DB_ID)
        cache["cached_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return cache["pages"]


def render_html(pages, elapsed):
    rows = ""
    for page in pages:
        props = page.get("properties") or {}
        rows += (
            "<li>"
            + unique_id_str(props.get("고유번호")) + " / "
            + plain_title(props.get("상호")) + " / "
            + plain_text(props.get("주소")) + " / "
            + select_name(props.get("카테고리")) + " / "
            + str(number_or_none(props.get("위도"))) + ", "
            + str(number_or_none(props.get("경도")))
            + "</li>"
        )

    return f"""
    <html>
      <head><meta charset="utf-8"><title>노션 DB 캐싱 테스트</title></head>
      <body>
        <h1>노션 DB 캐싱 테스트</h1>
        <p>총 {len(pages)}개 / 응답 시간 {elapsed:.3f}초 / 캐시 생성 시각: {cache["cached_at"]}</p>
        <p><a href="/refresh">캐시 강제 갱신 (노션 다시 조회)</a></p>
        <ul>{rows}</ul>
      </body>
    </html>
    """


# 캐시에서 바로 꺼내서 보여주는 경로 -> 대부분 빠르다
@app.get("/", response_class=HTMLResponse)
def index():
    start = time.time()
    pages = get_pages(force_refresh=False)
    elapsed = time.time() - start
    return render_html(pages, elapsed)


# 일부러 캐시를 무시하고 노션을 다시 조회하는 경로 -> 느린 걸 확인용
@app.get("/refresh", response_class=HTMLResponse)
def refresh():
    start = time.time()
    pages = get_pages(force_refresh=True)
    elapsed = time.time() - start
    return render_html(pages, elapsed)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
