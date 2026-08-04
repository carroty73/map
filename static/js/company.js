// static/js/company.js — 지도 페이지 전용
// 아이콘: static/ico/pack_2/
const ICON_DIR = "/static/ico/pack_2";
const iconFiles = {
  "볼 거리": "01_see.png",
  "알아갈 거리": "02_learn.png",
  "마실 거리": "03_drink.png",
  "먹을 거리": "04_eat.png",
  "즐길 거리": "05_play.png",
  "쉴 거리": "06_rest.png",
  "숙소": "07_stay.png",
  "교통": "08_move.png",
  "기타": "09_other.png",
};

const BOUNDARY_COLORS = [
  { fill: "#3388ff", line: "#1a4f99" },
  { fill: "#e67e00", line: "#a85a00" },
  { fill: "#27ae60", line: "#1e8449" },
  { fill: "#8e44ad", line: "#6c3483" },
  { fill: "#c0392b", line: "#922b21" },
  { fill: "#16a085", line: "#0e6655" },
];

let map = null;
let groups = {};
const placeIndex = [];
let blinkTimer = null;

function makeIcon(category) {
  const file = iconFiles[category] || iconFiles["기타"];
  return L.icon({
    iconUrl: ICON_DIR + "/" + file,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -12],
  });
}

function setSearchMsg(text, kind) {
  const el = document.getElementById("search-msg");
  if (!el) return;
  el.textContent = text || "";
  el.className = "company-search__msg" + (kind ? " is-" + kind : "");
}

function normalize(s) {
  return String(s || "").toLowerCase().replace(/\s+/g, "").trim();
}

function findPlaces(query) {
  const q = normalize(query);
  if (!q) return [];
  const exact = placeIndex.filter(function (p) { return normalize(p.name) === q; });
  if (exact.length) return exact;
  const byName = placeIndex.filter(function (p) { return normalize(p.name).indexOf(q) !== -1; });
  if (byName.length) return byName;
  return placeIndex.filter(function (p) { return normalize(p.address).indexOf(q) !== -1; });
}

function blinkMarker(marker) {
  const el = marker.getElement && marker.getElement();
  if (!el) return;
  el.classList.remove("blink-marker");
  void el.offsetWidth;
  el.classList.add("blink-marker");
  if (blinkTimer) clearTimeout(blinkTimer);
  blinkTimer = setTimeout(function () { el.classList.remove("blink-marker"); }, 3000);
}

function goToPlace(item) {
  if (item.group && map && !map.hasLayer(item.group)) map.addLayer(item.group);
  map.flyTo([item.lat, item.lon], 17, { duration: 0.85 });
  setTimeout(function () {
    item.marker.openPopup();
    blinkMarker(item.marker);
  }, 900);
}

function searchPlace(query) {
  const q = String(query || "").trim();
  if (!q) { setSearchMsg("검색어를 입력하세요.", "error"); return; }
  if (!map || !placeIndex.length) { setSearchMsg("아직 장소 데이터가 없습니다.", "error"); return; }
  const found = findPlaces(q);
  if (!found.length) { setSearchMsg(q + "을(를) 찾지 못했어요.", "error"); return; }
  const first = found[0];
  if (found.length === 1) setSearchMsg(first.name + " 으로 이동", "ok");
  else setSearchMsg(found.length + "곳 중 첫 결과: " + first.name, "ok");
  goToPlace(first);
}

function bindSearch() {
  const input = document.getElementById("search-input");
  const btn = document.getElementById("search-btn");
  if (!input || !btn) return;
  btn.addEventListener("click", function () { searchPlace(input.value); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); searchPlace(input.value); }
  });
}

function boundaryLabel(filename) {
  let name = String(filename || "");
  name = name.replace(/\.(txt|geojson|json)$/i, "");
  name = name.replace(/[ _]*바운더리리?/g, "");
  name = name.replace(/[ _]*boundary/gi, "");
  name = name.replace(/[ _]+/g, " ").trim();
  if (!name) name = filename;
  return name + " 경계";
}

async function loadBoundaries(overlays) {
  let list = [];
  try {
    const res = await fetch("/api/boundaries");
    if (res.ok) {
      const data = await res.json();
      list = data.boundaries || data || [];
    }
  } catch (e) {
    console.warn("바운더리 목록 API 실패", e);
  }

  if (!list.length) {
    list = [
      { name: "의정부 경계", url: "/api/boundary" },
      { name: "의정부 경계", url: "/uijeongbu_dong.geojson" },
    ];
  }

  let loaded = 0;
  for (let i = 0; i < list.length; i++) {
    const item = list[i];
    const url = item.url || ("/api/boundaries/" + encodeURIComponent(item.filename || item.id || ""));
    const label = item.name || boundaryLabel(item.filename || item.id || ("경계" + (i + 1)));
    const color = BOUNDARY_COLORS[i % BOUNDARY_COLORS.length];

    try {
      const bRes = await fetch(url);
      if (!bRes.ok) continue;
      const geo = await bRes.json();
      const layer = L.geoJSON(geo, {
        style: {
          fillColor: color.fill,
          color: color.line,
          weight: 2,
          fillOpacity: 0.08,
        },
      });
      layer.addTo(map);
      let key = label;
      let n = 2;
      while (overlays[key]) { key = label + " " + n; n++; }
      overlays[key] = layer;
      loaded++;
    } catch (e) {
      console.warn("바운더리 실패:", url, e);
    }
  }
  return loaded;
}

async function main() {
  bindSearch();

  const visitEl = document.getElementById("visit-count");
  fetch("/count.txt?" + Math.random())
    .then(function (r) { return r.text(); })
    .then(function (t) { if (visitEl) visitEl.innerText = t.trim(); })
    .catch(function () { if (visitEl) visitEl.innerText = "-"; });

  const res = await fetch("/api/places");
  if (!res.ok) throw new Error("API 실패: " + res.status);
  const data = await res.json();

  map = L.map("map").setView([data.map.lat, data.map.lon], data.map.zoom);

  const cartoLight = "https://" + "{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
  const cartoDark = "https://" + "{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
  const osm = "https://" + "{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

  const baseMaps = {
    "밝은 지도": L.tileLayer(cartoLight, { attribution: "&copy; OpenStreetMap, CARTO", maxZoom: 20 }),
    "어두운 지도": L.tileLayer(cartoDark, { attribution: "&copy; OpenStreetMap, CARTO", maxZoom: 20 }),
    "기본 지도": L.tileLayer(osm, { attribution: "&copy; OpenStreetMap", maxZoom: 19 }),
  };
  baseMaps["밝은 지도"].addTo(map);

  groups = {};
  const overlays = {};
  Object.keys(data.categoryVisible || {}).forEach(function (name) {
    groups[name] = L.layerGroup();
    overlays[name] = groups[name];
    if (data.categoryVisible[name]) groups[name].addTo(map);
  });

  await loadBoundaries(overlays);

  (data.places || []).forEach(function (p) {
    const group = groups[p.category] || groups["기타"];
    if (!group) return;
    const marker = L.marker([p.lat, p.lon], { icon: makeIcon(p.category), title: p.name });
    const safeName = String(p.name || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const safeCat = String(p.category || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const safeUrl = String(p.url || "#").replace(/"/g, "%22");
    marker.bindPopup(
      '<div class="company-popup">' +
        "<b>" + safeName + "</b><br/>" +
        "분류: " + safeCat + "<br/>" +
        '<a href="' + safeUrl + '" target="_blank" rel="noopener">📍 노션에서 확인</a>' +
      "</div>"
    );
    marker.addTo(group);
    placeIndex.push({
      name: p.name, address: p.address || "", category: p.category,
      lat: p.lat, lon: p.lon, marker: marker, group: group,
    });
  });

  L.control.layers(baseMaps, overlays, { collapsed: true }).addTo(map);

  const loading = document.getElementById("loading");
  if (loading) {
    loading.innerText = "장소 " + (data.count || 0) + "개 로드 완료";
    setTimeout(function () { loading.style.display = "none"; }, 1200);
  }
}

main().catch(function (err) {
  console.error(err);
  const loading = document.getElementById("loading");
  if (loading) loading.innerText = "불러오기 실패";
  alert("장소 데이터를 불러오지 못했습니다.");
});
