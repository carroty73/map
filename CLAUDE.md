# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(claude.ai/code)에게 안내를 제공합니다.

## 프로젝트 개요

Notion 데이터베이스에서 장소 데이터를 가져오고, Kakao로 주소를 지오코딩한 뒤,
Leaflet 지도를 렌더링하는 단일 파일 Flask 앱("당근이의 핫플 지도")입니다.
별도 프론트엔드 빌드 과정 없이 정적 HTML/CSS/JS를 Flask가 그대로 서빙합니다.

## 규칙

1. 사용자가 명시적으로 시킨 작업 외에는 아무것도 하지 않는다.
2. 실습의 편리함을 위해 코드가 수정될 때마다 FastAPI 서버를 스스로 재실행한다.

## 개발 방향

- 지역 기반 회사 소개 웹 애플리케이션을 개발할 것.
- Backend: Python(FastAPI). 참고: 현재 코드(`app.py`)는 Flask로 작성되어
  있으며, FastAPI로의 전환이 의도된 방향이지만 아직 진행되지 않았습니다.
- Frontend: `index.html` 단일 페이지 (별도 템플릿 페이지/SPA 프레임워크 없음).

## 앱 실행 방법

```
pip install flask python-dotenv requests
python app.py
```

`http://0.0.0.0:8001`에서 실행됩니다. 다음 항목이 담긴 `.env` 파일이 필요합니다
(커밋되지 않음):
- `NOTION_TOKEN` — Notion 통합 토큰
- `NOTION_HOT_DB_ID` — 핫플 DB의 Notion 데이터베이스 ID
- `NOTION_COMPANY_DB_ID` — 회사 DB의 Notion 데이터베이스 ID
- `kAKAO_REST_KEY` — Kakao 지오코딩 API 키
- `MY_IP` — 조회수 카운트에서 제외할 소유자 IP (선택, 미설정 시 전부 카운트)

이 저장소에는 별도의 빌드/린트/테스트 도구가 없습니다 — 작은 스크립트형 앱입니다.

## 아키텍처

- **`app.py`** — 백엔드 전체. 주요 역할:
  - `/`는 `templates/intro.html`(랜딩 페이지)을 렌더링합니다.
  - `/main`은 `send_file`로 `index.html`을 직접 서빙합니다(지도 페이지).
    이 라우트는 Jinja `url_for` 대신 `send_file`/`/static/...` 경로를 사용하므로,
    `index.html`의 에셋 URL은 하드코딩된 절대 경로입니다 — 정적 에셋을 이동/이름
    변경할 때 이 점을 유의해야 합니다.
  - `/api/places`는 핵심 데이터 엔드포인트입니다: Notion DB의 모든 행을 가져오고
    (`fetch_all_pages`, 페이지네이션 처리), 한글 이름의 Notion 속성(`상호`, `주소`,
    `카테고리`, `위도`, `경도`)을 읽어 `company.js`가 사용하는 JSON을 반환합니다.
    페이지에 위도/경도가 캐싱되어 있지 않으면 Kakao로 지오코딩하고
    (`get_kakao_coords`) 그 결과를 Notion에 다시 기록합니다
    (`update_notion_lat_lon`) — 이후 요청에서는 지오코딩 호출을 건너뛰도록 Notion이
    좌표 캐시 역할을 합니다.
  - `/count.txt`는 `count.txt`를 기반으로 한 간단한 방문자 수 카운터이며, 소유자의
    IP(`MY_IP`)는 카운트 증가에서 제외됩니다.
  - 경계/GeoJSON 라우트(`/api/boundaries`, `/api/boundaries/<filename>`, 레거시
    `/api/boundary`, `/uijeongbu_dong.geojson`)는 `boundaries/` 디렉터리(저장소에
    포함되지 않음; `.env`, `count.txt`와 함께 서버에 존재해야 함)에서 지역 경계
    오버레이를 서빙합니다. `_resolve_boundary_path`는 경로 순회(path traversal)를
    막고 있으므로, 이 코드를 수정할 때는 해당 검사를 유지해야 합니다.
  - `CATEGORY_VISIBLE`과 Notion의 `카테고리` 값이 지도 레이어 카테고리의 단일
    진실 공급원(source of truth)입니다; `static/js/company.js`의 `iconFiles`에는
    모든 카테고리에 대응하는 아이콘 항목이 있어야 하며, 없으면 "기타"로
    대체됩니다.

- **`static/js/company.js`** — 지도 페이지의 모든 로직: `/api/places`와
  `/api/boundaries`를 가져오고, 카테고리별 Leaflet 마커 레이어 그룹을 구성하며,
  순환 색상으로 경계 오버레이를 렌더링하고, 일치하는 마커로 이동해 깜빡이게 하는
  이름/주소 검색 박스(`findPlaces`/`goToPlace`)를 구현합니다.

- **`templates/intro.html`** vs **`index.html`**: intro는 Jinja로 렌더링되는
  랜딩 페이지(`url_for("static", ...)` 사용)이고, 지도 페이지(`index.html`)는
  그대로 서빙되는 정적 파일(하드코딩된 `/static/...` 경로)입니다 — 둘은 서로 다른
  에셋 참조 방식을 사용하므로, `index.html`을 수정할 때 `url_for`가 동작한다고
  가정하면 안 됩니다.

## 배포 관련 참고사항 (README.txt 기반)

- 공개되는 모든 파일은 `static/` 아래에 있으며, 별도의 `rsc` 디렉터리는 없습니다.
- `.env`, `count.txt`, `boundaries/`는 서버 측 상태이며 배포 간에 유지되어야
  합니다 — 추적되는 소스 트리에는 포함되지 않습니다.
- `index.html`의 OG 이미지/메타 URL은 서버 IP와 포트(`221.138.105.134:8001`)가
  하드코딩되어 있습니다 — 배포 호스트/포트가 바뀌면 이 값도 갱신해야 합니다.
