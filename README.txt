company — static only 최종본
============================

rsc 없음. 공개 파일은 전부 static/.

구조
----
company/
  app.py
  index.html                 → /company/
  templates/intro.html       → /
  static/
    css/intro.css, company.css
    js/intro.js, company.js
    img/coffee.png, company-og.png, hot-og.png
    ico/pack_1/, ico/pack_2/   ← 마커 아이콘

경로
----
- intro (Jinja): url_for("static", filename="...")
- index (send_file): /static/...
- 아이콘: /static/ico/pack_2/
- OG: /static/img/company-og.png

수정 요약
---------
1) ICON_DIR → /static/ico/pack_2
2) OG/이미지 rsc 제거 → static/img
3) coffee.png = carrot.png 복사, company-og.png = hot-og.png 복사
4) app.py 노션 PATCH URL 중괄호 버그 수정
5) 좌표 검사: is None
6) /rsc 라우트 주석 삭제
7) OG 포트 8001 (app.run 과 맞춤)

확인
----
  /static/css/company.css
  /static/js/company.js
  /static/ico/pack_2/01_see.png
  /static/img/coffee.png
  /static/img/company-og.png
  /
  /company/

서버에 둘 때
------------
.env, count.txt, boundaries/ 는 기존 것 유지.
