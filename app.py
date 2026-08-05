# ===== 설정 =====
import os
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_HOT_DB_ID = os.environ.get("NOTION_HOT_DB_ID")
NOTION_COMPANY_DB_ID = os.environ.get("NOTION_COMPANY_DB_ID")
KAKAO_API_KEY = os.environ.get("kAKAO_REST_KEY")

from flask import (
    Flask,
    send_file,
    send_from_directory,
    request,
    render_template,
    jsonify,
    abort,
)
import re
import requests
from urllib.parse import unquote

app = Flask(__name__)

COUNT_FILE = "count.txt"
MY_IP = "221.138.105.134"

MAP_LAT = 37.738060
MAP_LON = 127.046110
MAP_ZOOM = 13

CATEGORY_VISIBLE = {
    "hotspot": {
        "볼 거리": True,
        "알아갈 거리": True,
        "마실 거리": True,
        "먹을 거리": True,
        "즐길 거리": True,
        "쉴 거리": True,
        "숙소": True,
        "교통": True,
        "기타": True,
    },
    "company": {
        "서버SW": True,
        "펌웨어": True,
        "회로설계": True,
        "PCB 아트웍/제작": True,
        "SMT / 조립 / 하네스": True,
        "부품 유통": True,
        "기구설계 / CNC": True,
        "계측 / 시험 / 인증": True,
        "기타": True,
    },
}

DOMAINS = [
    {"key": "hotspot", "db_id": NOTION_HOT_DB_ID},
    {"key": "company", "db_id": NOTION_COMPANY_DB_ID},
]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
# =================


def fetch_all_pages(db_id):
    url = "https://" + "api.notion.com/v1/databases/" + db_id + "/query"
    results = []
    payload = {
        "page_size": 100,
        "filter": {
            "property": "숨김",
            "checkbox": {"equals": False}  # 숨김 아닌 것만
        }
    }   

    while True:
        res = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30).json()
        if "results" not in res:
            raise RuntimeError(f"Notion 응답 오류: {res}")
        results.extend(res["results"])
        if not res.get("has_more"):
            break
        payload["start_cursor"] = res["next_cursor"]
    return results


def get_kakao_coords(address):
    url = "https://" + "dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        data = requests.get(
            url,
            headers=headers,
            params={"query": address.strip()},
            timeout=5,
        ).json()
        docs = data.get("documents") or []
        if not docs:
            return None, None
        return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        print(f"카카오 오류: {e}")
        return None, None


# 노션 위도 경도 업데이트 함수 (api_places보다 위로 이동)
def update_notion_lat_lon(page_id, lat, lon):
    """노션 페이지의 '위도', '경도' 속성 값을 업데이트합니다."""
    url = "https://" + "api.notion.com/v1/pages/" + page_id
    payload = {
        "properties": {
            "위도": {"number": lat},
            "경도": {"number": lon}
        }
    }
    try:
        response = requests.patch(url, headers=NOTION_HEADERS, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"노션 위경도 캐싱 성공 (Page ID: {page_id}): ({lat}, {lon})")
        else:
            print(f"노션 위경도 캐싱 실패: {response.text}")
    except Exception as e:
        print(f"노션 위경도 업데이트 오류: {e}")


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


@app.route("/")
def index():
    return render_template("intro.html")


@app.route("/map")
def map_page():
    return send_file("index.html")


@app.route("/api/places")
def api_places():
    places = []
    for domain in DOMAINS:
        db_id = domain["db_id"]
        if not db_id:
            continue
        try:
            pages = fetch_all_pages(db_id)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        for page in pages:
            props = page.get("properties") or {}
            name = plain_title(props.get("상호"))
            address = plain_text(props.get("주소"))
            if not name or not address:
                continue

            category = select_name(props.get("카테고리"), "기타")

            # 1. 노션 DB에 이미 위도, 경도가 기록되어 있는지 확인
            lat = number_or_none(props.get("위도"))
            lon = number_or_none(props.get("경도"))

            # 2. 위도나 경도가 없다면 카카오 지오코딩 실행 후 노션에 저장
            if lat is None or lon is None:
                lat, lon = get_kakao_coords(address)
                if lat is not None and lon is not None:
                    page_id = page.get("id")
                    update_notion_lat_lon(page_id, lat, lon)

            if lat is None or lon is None:
                print(f"좌표 실패: {name} / {address}")
                continue

            places.append({
                "name": name,
                "address": address,
                "category": category,
                "domain": domain["key"],
                "lat": lat,
                "lon": lon,
                "url": page.get("url", "#"),
            })

    return jsonify({
        "map": {
            "lat": MAP_LAT,
            "lon": MAP_LON,
            "zoom": MAP_ZOOM,
        },
        "categoryVisible": CATEGORY_VISIBLE,
        "places": places,
        "count": len(places),
    })


DB_ID_BY_DOMAIN = {d["key"]: d["db_id"] for d in DOMAINS}


def create_notion_place(db_id, name, address, category, lat, lon, phone, memo):
    url = "https://" + "api.notion.com/v1/pages"
    properties = {
        "상호": {"title": [{"text": {"content": name}}]},
        "주소": {"rich_text": [{"text": {"content": address}}]},
        "카테고리": {"select": {"name": category}},
        "위도": {"number": lat},
        "경도": {"number": lon},
        "숨김": {"checkbox": False},
    }
    if phone:
        properties["전화번호"] = {"phone_number": phone}
    if memo:
        properties["메모"] = {"rich_text": [{"text": {"content": memo}}]}

    payload = {"parent": {"database_id": db_id}, "properties": properties}
    res = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=15)
    if res.status_code not in (200, 201):
        raise RuntimeError(f"노션 등록 실패: {res.status_code} {res.text}")
    return res.json()


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    domain = data.get("domain")
    name = (data.get("name") or "").strip()
    address = (data.get("address") or "").strip()
    category = (data.get("category") or "기타").strip()
    phone = (data.get("phone") or "").strip()
    memo = (data.get("memo") or "").strip()

    if domain not in DB_ID_BY_DOMAIN or not DB_ID_BY_DOMAIN[domain]:
        return jsonify({"error": "잘못된 분류입니다."}), 400
    if not name or not address:
        return jsonify({"error": "상호와 주소를 입력해주세요."}), 400
    if category not in CATEGORY_VISIBLE.get(domain, {}):
        return jsonify({"error": "잘못된 카테고리입니다."}), 400

    lat, lon = get_kakao_coords(address)
    if lat is None or lon is None:
        return jsonify({"error": "주소로 좌표를 찾지 못했습니다. 주소를 다시 확인해주세요."}), 400

    try:
        page = create_notion_place(
            DB_ID_BY_DOMAIN[domain], name, address, category, lat, lon, phone, memo
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "place": {
            "name": name,
            "address": address,
            "category": category,
            "domain": domain,
            "lat": lat,
            "lon": lon,
            "url": page.get("url", "#"),
        }
    })


@app.route("/count.txt")
def get_count():
    if request.remote_addr != MY_IP:
        if not os.path.exists(COUNT_FILE):
            count = 1
        else:
            with open(COUNT_FILE, "r") as f:
                count = int(f.read()) + 1
        with open(COUNT_FILE, "w") as f:
            f.write(str(count))
    else:
        count = open(COUNT_FILE).read() if os.path.exists(COUNT_FILE) else 0
    return str(count)


# ============================================================
# 여러 지역 바운더리 지원
# ============================================================
BOUNDARIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boundaries")
BOUNDARY_EXTS = {".txt", ".geojson", ".json"}
LEGACY_BOUNDARY_FILES = [
    "uijeongbu_dong.geojson",
]


def _boundary_display_name(filename: str) -> str:
    name = filename
    name = re.sub(r"\.(txt|geojson|json)$", "", name, flags=re.I)
    name = re.sub(r"[ _]*바운더리리?", "", name)
    name = re.sub(r"[ _]*boundary", "", name, flags=re.I)
    name = re.sub(r"[ _]*hangjeongdong[ _]*", " ", name, flags=re.I)
    name = re.sub(r"[ _]+", " ", name).strip()
    if not name:
        name = filename
    return f"{name} 경계"


def _list_boundary_files():
    items = []
    seen = set()

    if os.path.isdir(BOUNDARIES_DIR):
        for fn in sorted(os.listdir(BOUNDARIES_DIR)):
            path = os.path.join(BOUNDARIES_DIR, fn)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in BOUNDARY_EXTS:
                continue
            if fn in seen:
                continue
            seen.add(fn)
            items.append({
                "id": fn,
                "filename": fn,
                "name": _boundary_display_name(fn),
                "url": f"/api/boundaries/{fn}",
                "source": "boundaries/",
            })

    root = os.path.dirname(os.path.abspath(__file__))
    for fn in LEGACY_BOUNDARY_FILES:
        path = os.path.join(root, fn)
        if os.path.isfile(path) and fn not in seen:
            seen.add(fn)
            items.append({
                "id": fn,
                "filename": fn,
                "name": _boundary_display_name(fn),
                "url": f"/api/boundaries/{fn}",
                "source": "root",
            })

    return items


def _resolve_boundary_path(filename: str):
    filename = unquote(filename)
    if "/" in filename or "\\" in filename or ".." in filename:
        return None

    candidates = [
        os.path.join(BOUNDARIES_DIR, filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in BOUNDARY_EXTS or filename in LEGACY_BOUNDARY_FILES:
                return path
    return None


@app.route("/api/boundaries")
def api_boundaries_list():
    items = _list_boundary_files()
    return jsonify({"boundaries": items, "count": len(items)})


@app.route("/api/boundaries/<path:filename>")
def api_boundary_file(filename):
    path = _resolve_boundary_path(filename)
    if not path:
        abort(404)
    directory = os.path.dirname(path)
    fn = os.path.basename(path)
    return send_from_directory(directory, fn)


@app.route("/api/boundary")
def api_boundary_legacy():
    items = _list_boundary_files()
    if not items:
        abort(404)
    return api_boundary_file(items[0]["filename"])


@app.route("/uijeongbu_dong.geojson")
def uijeongbu_geojson_legacy():
    path = _resolve_boundary_path("uijeongbu_dong.geojson")
    if path:
        return send_file(path)
    for it in _list_boundary_files():
        if "의정부" in it["filename"]:
            return api_boundary_file(it["filename"])
    abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)