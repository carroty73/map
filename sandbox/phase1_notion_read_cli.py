# Phase 1 실험: 노션 DB를 읽는 것만 한다. (Kakao 지오코딩, FastAPI 등은 다루지 않음)
# 결과는 터미널에 print로 출력한다. (브라우저로 보는 버전은 phase1_notion_read_web.py)
import os
from dotenv import load_dotenv  # .env 파일의 값을 환경변수로 불러오는 라이브러리
import requests  # HTTP 요청(노션 API 호출)을 보내는 라이브러리

load_dotenv()  # .env 파일을 읽어서 os.environ에 등록
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")  # 노션 통합(integration) 인증 토큰
NOTION_DB_ID = os.environ.get("NOTION_COMPANY_DB_ID")  # 조회할 노션 데이터베이스 ID

# 노션 API를 호출할 때 매번 붙여야 하는 공통 헤더
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def fetch_all_pages(db_id):
    """노션 DB의 모든 행(페이지)을 가져온다. (app.py의 fetch_all_pages와 동일)

    노션 API는 한 번에 최대 100개까지만 주기 때문에,
    응답의 has_more가 True인 동안 next_cursor로 다음 페이지를 계속 요청한다.
    """
    url = "https://" + "api.notion.com/v1/databases/" + db_id + "/query"
    results = []
    payload = {
        "page_size": 100,
        # "숨김" 체크박스가 켜진(True) 행은 제외하고 가져온다
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
        payload["start_cursor"] = res["next_cursor"]  # 다음 페이지 요청을 위한 커서
    return results


# 아래 4개 함수는 노션 API 응답(JSON)에서 실제 값만 꺼내는 헬퍼 함수들이다.
# 노션은 속성 종류(제목/텍스트/선택/숫자)마다 JSON 구조가 다르기 때문에
# 타입별로 값을 꺼내는 방법이 다르다.

def plain_title(prop):
    """제목(title) 타입 속성에서 순수 텍스트만 꺼낸다. (예: 상호)"""
    arr = (prop or {}).get("title") or []
    return arr[0]["plain_text"] if arr else ""


def plain_text(prop):
    """텍스트(rich_text) 타입 속성에서 순수 텍스트만 꺼낸다. (예: 주소)"""
    arr = (prop or {}).get("rich_text") or []
    return arr[0]["plain_text"] if arr else ""


def select_name(prop, default="기타"):
    """선택(select) 타입 속성에서 선택된 값을 꺼낸다. 없으면 default. (예: 카테고리)"""
    sel = (prop or {}).get("select")
    if not sel:
        return default
    return sel.get("name") or default


def number_or_none(prop):
    """숫자(number) 타입 속성값을 꺼낸다. 값이 없으면 None. (예: 위도/경도)"""
    if not prop:
        return None
    return prop.get("number")


# 이 파일을 직접 실행했을 때만(python phase1_notion_read_cli.py) 동작
if __name__ == "__main__":
    pages = fetch_all_pages(NOTION_DB_ID)
    print(f"총 {len(pages)}개 페이지 조회됨\n")

    for page in pages:
        props = page.get("properties") or {}
        # 필요한 속성만 뽑아서 딕셔너리로 만들어 한 줄씩 출력
        print({
            "상호": plain_title(props.get("상호")),
            "주소": plain_text(props.get("주소")),
            "카테고리": select_name(props.get("카테고리")),
            "위도": number_or_none(props.get("위도")),
            "경도": number_or_none(props.get("경도")),
        })
