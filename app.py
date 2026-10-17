import base64
from datetime import datetime, timedelta
import json
import math
import urllib.parse
import folium
from geopy.distance import geodesic
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

# ----------------- 頁面基本設定 -----------------
st.set_page_config(
    page_title="截圖轉行程 Travel Pin-to-Itinerary 3D",
    page_icon="✈️",
    layout="wide",
)

# 自訂頂部視覺樣式
st.markdown(
    """
    <style>
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #0284c7 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.2rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
    }
    .hero-banner h1 {
        margin: 0 0 0.4rem 0;
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
    }
    .hero-banner p {
        margin: 0;
        font-size: 1rem;
        color: #e0f2fe;
        opacity: 0.95;
    }
    .stat-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        text-align: center;
    }
    .stat-val {
        font-size: 1.45rem;
        font-weight: 800;
        color: #0f172a;
    }
    .stat-label {
        font-size: 0.82rem;
        color: #64748b;
    }
    </style>
    <div class="hero-banner">
        <h1>✈️ 上班截圖、下班出發：社畜無腦排行程 AI (3D 實景漫遊版)</h1>
        <p>IG、小紅書截圖一鍵丟！AI 自動抓出神秘景點、最佳化順路動線，還能讓 3D 分身先幫你在地圖上走一遍！</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- 內建駭客松 Demo 範例資料 -----------------
DEMO_ITINERARIES = {
    "🇯🇵 日本京都｜清水寺周邊一日漫遊 (5 站)": [
        {
            "name": "伏見稻荷大社",
            "city": "日本京都",
            "category": "景點",
            "must_try_or_see": "千本鳥居晨間光影拍照",
            "lat": 34.9671,
            "lon": 135.7727,
            "stay_mins": 75,
            "price_est": "免費參觀",
            "best_time": "上午",
        },
        {
            "name": "清水寺",
            "city": "日本京都",
            "category": "景點",
            "must_try_or_see": "清水舞台遠眺京都塔",
            "lat": 34.9949,
            "lon": 135.7850,
            "stay_mins": 90,
            "price_est": "¥500",
            "best_time": "上午",
        },
        {
            "name": "藤菜美 三年坂本店",
            "city": "日本京都",
            "category": "美食",
            "must_try_or_see": "現烤醬油糰子配洛水抹茶",
            "lat": 34.9964,
            "lon": 135.7812,
            "stay_mins": 45,
            "price_est": "¥1,200",
            "best_time": "下午茶",
        },
        {
            "name": "八坂神社 & 祇園花見小路",
            "city": "日本京都",
            "category": "景點",
            "must_try_or_see": "舞殿提燈與町家古街抓拍",
            "lat": 35.0037,
            "lon": 135.7785,
            "stay_mins": 60,
            "price_est": "免費參觀",
            "best_time": "傍晚",
        },
        {
            "name": "先斗町 柚子元",
            "city": "日本京都",
            "category": "美食",
            "must_try_or_see": "鴨川旁必吃黃金柚子鍋與煎餃",
            "lat": 35.0067,
            "lon": 135.7711,
            "stay_mins": 90,
            "price_est": "¥3,500",
            "best_time": "晚餐",
        },
    ],
    "🇹🇼 台灣台北｜大稻埕老街與河岸微醺 (5 站)": [
        {
            "name": "慈聖宮廟口原汁排骨湯",
            "city": "台灣台北",
            "category": "美食",
            "must_try_or_see": "老榕樹下吃排骨湯配高麗菜飯",
            "lat": 25.0598,
            "lon": 121.5105,
            "stay_mins": 50,
            "price_est": "NT$150",
            "best_time": "午餐",
        },
        {
            "name": "迪化街十連棟 & 老宅巡禮",
            "city": "台灣台北",
            "category": "景點",
            "must_try_or_see": "巴洛克紅磚拱廊復古街拍",
            "lat": 25.0612,
            "lon": 121.5091,
            "stay_mins": 60,
            "price_est": "免費參觀",
            "best_time": "下午",
        },
        {
            "name": "幻猻家珈琲 Pallas Café",
            "city": "台灣台北",
            "category": "美食",
            "must_try_or_see": "招牌焦糖布丁與手沖單品",
            "lat": 25.0566,
            "lon": 121.5096,
            "stay_mins": 65,
            "price_est": "NT$320",
            "best_time": "下午茶",
        },
        {
            "name": "台北霞海城隍廟 & 永樂市場",
            "city": "台灣台北",
            "category": "購物",
            "must_try_or_see": "求月老紅線、逛文創布業小店",
            "lat": 25.0554,
            "lon": 121.5102,
            "stay_mins": 45,
            "price_est": "NT$200",
            "best_time": "下午",
        },
        {
            "name": "大稻埕碼頭貨櫃市集",
            "city": "台灣台北",
            "category": "景點",
            "must_try_or_see": "淡水河夕陽第一排微醺看夜景",
            "lat": 25.0568,
            "lon": 121.5067,
            "stay_mins": 90,
            "price_est": "NT$400",
            "best_time": "傍晚/夜景",
        },
    ],
}

# 備援模型清單（修正為真實有效的 Gemini Vision 模型）
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

# ----------------- 側邊欄：API 金鑰與 Demo 模式 -----------------
st.sidebar.header("🎯 駭客松快速體驗")
demo_choice = st.sidebar.selectbox(
    "免上傳！一鍵載入範例行程：",
    options=list(DEMO_ITINERARIES.keys()),
)
if st.sidebar.button("✨ 載入 Demo 行程（立即可玩 3D）", use_container_width=True):
  st.session_state["places"] = [
      dict(item) for item in DEMO_ITINERARIES[demo_choice]
  ]
  st.toast(f"已載入：{demo_choice}", icon="🎉")

st.sidebar.markdown("---")
st.sidebar.header("🔑 Gemini API 設定")
st.sidebar.markdown(
    "上傳真實截圖需使用 Google Gemini API。\n"
    "[👉 點此免費取得 Gemini API Key](https://aistudio.google.com/app/apikey)"
)

user_key = st.sidebar.text_input(
    "請輸入您的 Gemini API Key",
    value="",
    type="password",
    placeholder="AIzaSy...",
    help="金鑰僅供本次瀏覽階段使用，若只體驗上方 Demo 可不必輸入。",
)

clean_api_key = user_key.strip().strip('"').strip("'") if user_key else ""

if st.sidebar.button("🔍 測試 Key 連線狀態", use_container_width=True):
  if not clean_api_key:
    st.sidebar.error("請先輸入 API Key！")
  else:
    success = False
    last_msg = ""
    for model_name in MODELS_TO_TRY:
      test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_api_key}"
      payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
      try:
        res = requests.post(test_url, json=payload, timeout=10)
        if res.status_code == 200:
          st.sidebar.success(f"✅ 連線成功！可用模型：{model_name}")
          success = True
          break
        else:
          last_msg = f"{model_name} ({res.status_code})"
      except Exception as e:
        last_msg = f"{model_name}: {e}"
    if not success:
      st.sidebar.error(f"❌ 連線失敗：{last_msg}")

# ----------------- 側邊欄：上傳與觸發按鈕 -----------------
st.sidebar.markdown("---")
st.sidebar.header("📸 上傳旅遊截圖")
uploaded_files = st.sidebar.file_uploader(
    "支援多張 IG / 小紅書 / Google Maps 截圖",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)
start_button = st.sidebar.button(
    "🚀 開始 AI 辨識並排程", type="primary", use_container_width=True
)


# ----------------- 輔助函式：路徑智慧排序 (TSP 貪婪演算法 + 起點可選) -----------------
def optimize_route(places_list, start_idx=0):
  """依據地理距離排序，以指定索引景點為起點，每次挑選距離最近的下一個點。"""
  valid_places = [
      p
      for p in places_list
      if p.get("lat") is not None and p.get("lon") is not None
  ]
  no_coords = [
      p for p in places_list if p.get("lat") is None or p.get("lon") is None
  ]

  if len(valid_places) <= 2:
    return valid_places + no_coords

  start_idx = max(0, min(start_idx, len(valid_places) - 1))
  current = valid_places[start_idx]
  unvisited = [p for idx, p in enumerate(valid_places) if idx != start_idx]
  optimized = [current]

  while unvisited:
    current_coord = (current["lat"], current["lon"])
    next_place = min(
        unvisited,
        key=lambda p: geodesic(current_coord, (p["lat"], p["lon"])).kilometers,
    )
    optimized.append(next_place)
    unvisited.remove(next_place)
    current = next_place

  return optimized + no_coords


# ----------------- 輔助函式：計算各段距離、時間與時間軸 -----------------
def enrich_route_metrics(
    places_list, start_time_str="09:30", travel_mode="walking", pace_factor=1.0
):
  """為每個景點加上與前一站距離、交通時間、抵達與離開時間。"""
  speed_kmh = {"walking": 4.5, "transit": 18.0, "driving": 28.0}.get(
      travel_mode, 4.5
  )
  curr_time = datetime.strptime(start_time_str, "%H:%M")

  enriched = []
  total_km = 0.0
  total_move_mins = 0
  total_stay_mins = 0

  for i, p in enumerate(places_list):
    item = dict(p)
    if i == 0:
      item["dist_from_prev_km"] = 0.0
      item["move_mins_from_prev"] = 0
    else:
      prev = enriched[i - 1]
      if (
          prev.get("lat")
          and prev.get("lon")
          and item.get("lat")
          and item.get("lon")
      ):
        dist = geodesic(
            (prev["lat"], prev["lon"]), (item["lat"], item["lon"])
        ).kilometers
        # 考量城市道路彎曲係數 1.28
        road_dist = round(dist * 1.28, 2)
      else:
        road_dist = 0.8
      move_mins = max(3, int(round((road_dist / speed_kmh) * 60)))
      if travel_mode == "transit":
        move_mins += 6  # 等車緩衝
      item["dist_from_prev_km"] = road_dist
      item["move_mins_from_prev"] = move_mins
      total_km += road_dist
      total_move_mins += move_mins
      curr_time += timedelta(minutes=move_mins)

    stay_base = int(item.get("stay_mins") or 60)
    stay_mins = max(20, int(round(stay_base * pace_factor)))
    item["stay_mins_adjusted"] = stay_mins
    item["arrive_time"] = curr_time.strftime("%H:%M")
    curr_time += timedelta(minutes=stay_mins)
    item["depart_time"] = curr_time.strftime("%H:%M")
    total_stay_mins += stay_mins
    enriched.append(item)

  summary = {
      "total_km": round(total_km, 2),
      "total_move_mins": total_move_mins,
      "total_stay_mins": total_stay_mins,
      "end_time": curr_time.strftime("%H:%M"),
      "calories": int(round(total_km * 55))
      if travel_mode == "walking"
      else int(round(total_km * 18)),
  }
  return enriched, summary


# ----------------- 輔助函式：生成 Google Maps 多點導航連結 -----------------
def generate_google_maps_directions_url(places_list, travel_mode="walking"):
  valid_places = [
      p for p in places_list if p.get("name") and p.get("lat") and p.get("lon")
  ]
  if len(valid_places) < 2:
    return None

  origin = urllib.parse.quote(
      f"{valid_places[0]['name']} {valid_places[0].get('city', '')}"
  )
  destination = urllib.parse.quote(
      f"{valid_places[-1]['name']} {valid_places[-1].get('city', '')}"
  )

  if len(valid_places) > 2:
    waypoint_names = [
        f"{p['name']} {p.get('city', '')}" for p in valid_places[1:-1]
    ]
    waypoints = urllib.parse.quote("|".join(waypoint_names))
    return (
        f"https://www.google.com/maps/dir/?api=1&origin={origin}"
        f"&destination={destination}&waypoints={waypoints}&travelmode={travel_mode}"
    )
  return (
      f"https://www.google.com/maps/dir/?api=1&origin={origin}"
      f"&destination={destination}&travelmode={travel_mode}"
  )


# ----------------- 輔助函式：生成 .ics 行事曆檔案 -----------------
def generate_ics_content(enriched_places):
  today_str = datetime.now().strftime("%Y%m%d")
  lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Travel Pin-to-Itinerary AI//TW",
      "CALSCALE:GREGORIAN",
  ]
  for idx, p in enumerate(enriched_places, 1):
    dt_start = f"{today_str}T{p['arrive_time'].replace(':', '')}00"
    dt_end = f"{today_str}T{p['depart_time'].replace(':', '')}00"
    summary = f"第{idx}站：{p.get('name', '景點')} ({p.get('category', '行程')})"
    desc = f"推薦亮點：{p.get('must_try_or_see', '')} | 預估花費：{p.get('price_est', '依現場為準')}"
    loc = f"{p.get('name', '')} {p.get('city', '')}".strip()
    lines.extend([
        "BEGIN:VEVENT",
        f"DTSTART:{dt_start}",
        f"DTEND:{dt_end}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{desc}",
        f"LOCATION:{loc}",
        "END:VEVENT",
    ])
  lines.append("END:VCALENDAR")
  return "\r\n".join(lines)


# ----------------- 核心解析函式（多模型動態備援 REST 呼叫） -----------------
def analyze_image(file_obj):
  image_bytes = file_obj.getvalue()
  mime_type = (
      "image/png" if file_obj.name.lower().endswith(".png") else "image/jpeg"
  )
  encoded_image = base64.b64encode(image_bytes).decode("utf-8")

  prompt = """
    你是一個專業的旅遊行程規劃助手。請分析使用者上傳的這張旅遊/美食/景點截圖，並提取出核心的地點資訊。
    若一張圖包含多個推薦地點請全部列出。
    請務必嚴格輸出為 JSON 陣列格式，格式範例：
    [
      {
        "name": "地點名稱（最精確的中/原文店名或景點名）",
        "city": "所在城市/地區（例如：日本京都、台灣台北）",
        "category": "美食 / 景點 / 購物 / 住宿",
        "must_try_or_see": "推薦招牌菜或拍照亮點（15字以內）",
        "lat": 粗估緯度(float),
        "lon": 粗估經度(float),
        "stay_mins": 建議停留分鐘數(int，例如 60),
        "price_est": "預估人均消費（例如 NT$200 或 免費參觀）",
        "best_time": "建議時段（上午 / 午餐 / 下午茶 / 傍晚 / 晚餐）"
      }
    ]
    """

  payload = {
      "contents": [{
          "parts": [
              {"text": prompt},
              {
                  "inline_data": {
                      "mime_type": mime_type,
                      "data": encoded_image,
                  }
              },
          ]
      }],
      "generationConfig": {
          "response_mime_type": "application/json",
          "temperature": 0.2,
      },
  }

  headers = {"Content-Type": "application/json"}
  errors = []

  for model_name in MODELS_TO_TRY:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_api_key}"
    try:
      res = requests.post(url, headers=headers, json=payload, timeout=35)
      if res.status_code == 200:
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
      else:
        errors.append(f"{model_name} (HTTP {res.status_code})")
    except Exception as e:
      errors.append(f"{model_name} ({e})")

  st.error("所有備援模型皆呼叫失敗：\n" + "\n".join(errors))
  return []


# ----------------- 3D 旅人漫遊地圖組件 (MapLibre 3D + 動畫角色) -----------------
def render_3d_walking_map(enriched_places, travel_mode="walking"):
  """使用 MapLibre GL JS 建立 60 度傾斜 3D 立體地圖與可互動的 3D 行走小人。"""
  valid_places = [
      p
      for p in enriched_places
      if p.get("lat") is not None and p.get("lon") is not None
  ]
  if not valid_places:
    st.warning("無有效座標可供渲染 3D 地圖。")
    return

  places_json = json.dumps(valid_places, ensure_ascii=False)
  avatar_emoji = {"walking": "🧑‍🦯", "transit": "🚋", "driving": "🚗"}.get(
      travel_mode, "🚶"
  )

  html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
      <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
      <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        #map-wrapper {{
          position: relative;
          width: 100%;
          height: 580px;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
          border: 1px solid #cbd5e1;
        }}
        #map {{ width: 100%; height: 100%; }}

        /* 頂部 RPG 狀態資訊列 */
        .hud-top {{
          position: absolute;
          top: 14px;
          left: 14px;
          right: 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
          pointer-events: none;
          z-index: 10;
        }}
        .hud-badge {{
          background: rgba(15, 23, 42, 0.86);
          backdrop-filter: blur(8px);
          color: #f8fafc;
          padding: 10px 16px;
          border-radius: 12px;
          font-size: 13px;
          box-shadow: 0 4px 15px rgba(0,0,0,0.25);
          border: 1px solid rgba(255,255,255,0.15);
          pointer-events: auto;
        }}
        .hud-badge strong {{
          color: #38bdf8;
          font-size: 14px;
        }}

        /* 底部播放控制面板 */
        .control-bar {{
          position: absolute;
          bottom: 16px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(15, 23, 42, 0.90);
          backdrop-filter: blur(10px);
          padding: 10px 18px;
          border-radius: 999px;
          display: flex;
          align-items: center;
          gap: 10px;
          z-index: 10;
          box-shadow: 0 8px 25px rgba(0,0,0,0.35);
          border: 1px solid rgba(255,255,255,0.18);
          color: white;
          white-space: nowrap;
        }}
        .ctrl-btn {{
          background: #2563eb;
          color: white;
          border: none;
          padding: 7px 14px;
          border-radius: 999px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
        }}
        .ctrl-btn:hover {{ background: #1d4ed8; transform: translateY(-1px); }}
        .ctrl-btn.secondary {{ background: #334155; }}
        .ctrl-btn.secondary:hover {{ background: #475569; }}
        .speed-select {{
          background: #1e293b;
          color: #e2e8f0;
          border: 1px solid #475569;
          border-radius: 8px;
          padding: 5px 8px;
          font-size: 12px;
        }}

        /* 3D 旅人立體角色與腳步動畫 */
        .traveler-container {{
          position: relative;
          width: 68px;
          height: 84px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: flex-end;
          pointer-events: none;
        }}
        .speech-bubble {{
          position: absolute;
          bottom: 78px;
          background: #ffffff;
          color: #0f172a;
          padding: 7px 11px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 700;
          white-space: nowrap;
          box-shadow: 0 6px 18px rgba(0,0,0,0.22);
          border: 2px solid #2563eb;
          transition: all 0.2s ease;
        }}
        .speech-bubble::after {{
          content: "";
          position: absolute;
          bottom: -7px;
          left: 50%;
          transform: translateX(-50%);
          border-width: 7px 7px 0;
          border-style: solid;
          border-color: #2563eb transparent;
        }}
        .avatar-body {{
          width: 52px;
          height: 58px;
          position: relative;
          transform-origin: bottom center;
        }}
        .avatar-walking {{
          animation: bobbing 0.42s infinite alternate ease-in-out;
        }}
        @keyframes bobbing {{
          0% {{ transform: translateY(0px) rotate(-5deg) scale(1.02); }}
          100% {{ transform: translateY(-9px) rotate(5deg) scale(1.06); }}
        }}
        .avatar-shadow {{
          width: 34px;
          height: 11px;
          background: rgba(15, 23, 42, 0.42);
          border-radius: 50%;
          filter: blur(2px);
          margin-top: -4px;
        }}

        /* 站點 3D 立柱地標 */
        .stop-pin {{
          background: linear-gradient(135deg, #2563eb, #0ea5e9);
          color: white;
          font-weight: 800;
          font-size: 12px;
          padding: 4px 9px;
          border-radius: 999px;
          border: 2px solid white;
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          cursor: pointer;
          transition: transform 0.2s;
        }}
        .stop-pin:hover {{ transform: scale(1.18); }}
        .stop-pin.active {{
          background: linear-gradient(135deg, #f59e0b, #ef4444);
          transform: scale(1.22);
        }}
      </style>
    </head>
    <body>
      <div id="map-wrapper">
        <div id="map"></div>

        <div class="hud-top">
          <div class="hud-badge" id="status-box">
            <strong>🕹️ 3D 實景預演模式</strong><br/>
            <span id="status-text">準備從第 1 站出發！點擊下方「自動漫遊」看 3D 旅人走訪全程</span>
          </div>
          <div class="hud-badge" style="text-align:right;">
            <div>🕒 當前時段：<strong id="hud-time">--:--</strong></div>
            <div>👟 累積路程：<strong id="hud-dist">0.00 km</strong> (<span id="hud-boba">0.0</span> 杯珍奶🧋)</div>
          </div>
        </div>

        <div class="control-bar">
          <button class="ctrl-btn" id="btn-play" onclick="togglePlay()">▶️ 自動漫遊</button>
          <button class="ctrl-btn secondary" onclick="stepPrev()">⏮️ 上一站</button>
          <button class="ctrl-btn secondary" onclick="stepNext()">⏭️ 下一站</button>
          <button class="ctrl-btn secondary" onclick="toggleCameraFollow()" id="btn-cam">🎥 視角：跟隨</button>
          <select class="speed-select" id="speed-sel" onchange="changeSpeed()">
            <option value="1">速度 1x</option>
            <option value="2" selected>速度 2x</option>
            <option value="4">速度 4x</option>
          </select>
        </div>
      </div>

      <script>
        const places = {places_json};
        let currentIndex = 0;
        let isPlaying = false;
        let followCam = true;
        let speedMultiplier = 2;
        let animFrame = null;

        // 初始化 MapLibre 3D 傾斜地圖
        const map = new maplibregl.Map({{
          container: 'map',
          style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
          center: [places[0].lon, places[0].lat],
          zoom: 15.2,
          pitch: 62,
          bearing: -18,
          antialias: true
        }});

        map.addControl(new maplibregl.NavigationControl({{ visualizePitch: true }}), 'top-right');

        const stopMarkers = [];

        // 建立 3D SVG 立體背包客小人
        const travelerEl = document.createElement('div');
        travelerEl.className = 'traveler-container';
        travelerEl.innerHTML = `
          <div class="speech-bubble" id="bubble-text">📍 第 1 站：${{places[0].name}}</div>
          <div class="avatar-body" id="avatar-sprite">
            <svg viewBox="0 0 64 72" width="52" height="58">
              <!-- 背包 -->
              <rect x="10" y="26" width="12" height="22" rx="5" fill="#ea580c" stroke="#fff" stroke-width="2"/>
              <!-- 身體外套 -->
              <rect x="18" y="24" width="26" height="26" rx="9" fill="#2563eb" stroke="#fff" stroke-width="2.5"/>
              <!-- 頭部 -->
              <circle cx="32" cy="14" r="11" fill="#fde68a" stroke="#fff" stroke-width="2.5"/>
              <!-- 太陽眼鏡 -->
              <rect x="26" y="10" width="16" height="6" rx="3" fill="#0f172a"/>
              <!-- 雙腳 -->
              <rect x="21" y="48" width="8" height="14" rx="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>
              <rect x="33" y="48" width="8" height="14" rx="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>
            </svg>
          </div>
          <div class="avatar-shadow"></div>
        `;

        const travelerMarker = new maplibregl.Marker({{ element: travelerEl, anchor: 'bottom' }})
          .setLngLat([places[0].lon, places[0].lat])
          .addTo(map);

        map.on('load', () => {{
          const routeCoords = places.map(p => [p.lon, p.lat]);

          // 完整路線底線
          map.addSource('route-base', {{
            type: 'geojson',
            data: {{
              type: 'Feature',
              geometry: {{ type: 'LineString', coordinates: routeCoords }}
            }}
          }});

          map.addLayer({{
            id: 'route-glow',
            type: 'line',
            source: 'route-base',
            layout: {{ 'line-join': 'round', 'line-cap': 'round' }},
            paint: {{
              'line-color': '#38bdf8',
              'line-width': 10,
              'line-opacity': 0.35
            }}
          }});

          map.addLayer({{
            id: 'route-line',
            type: 'line',
            source: 'route-base',
            layout: {{ 'line-join': 'round', 'line-cap': 'round' }},
            paint: {{
              'line-color': '#2563eb',
              'line-width': 5,
              'line-dasharray': [2, 1.5]
            }}
          }});

          // 已走過的高亮路線
          map.addSource('route-walked', {{
            type: 'geojson',
            data: {{
              type: 'Feature',
              geometry: {{ type: 'LineString', coordinates: [routeCoords[0]] }}
            }}
          }});

          map.addLayer({{
            id: 'route-walked-line',
            type: 'line',
            source: 'route-walked',
            layout: {{ 'line-join': 'round', 'line-cap': 'round' }},
            paint: {{
              'line-color': '#f59e0b',
              'line-width': 6
            }}
          }});

          // 放置每一站標記
          places.forEach((p, idx) => {{
            const pin = document.createElement('div');
            pin.className = 'stop-pin' + (idx === 0 ? ' active' : '');
            pin.innerHTML = `${{idx + 1}}. ${{p.name}}`;
            pin.onclick = () => jumpToStop(idx);

            const m = new maplibregl.Marker({{ element: pin, anchor: 'bottom' }})
              .setLngLat([p.lon, p.lat])
              .setPopup(new maplibregl.Popup({{ offset: 25 }}).setHTML(
                `<b>第 ${{idx + 1}} 站：${{p.name}}</b><br/>` +
                `🕒 ${{p.arrive_time}} - ${{p.depart_time}}<br/>` +
                `💡 必看/必吃：${{p.must_try_or_see}}`
              ))
              .addTo(map);
            stopMarkers.push(pin);
          }});

          updateHudAtStop(0);
        }});

        function calcCumDist(uptoIndex, partialFraction = 0) {{
          let d = 0;
          for (let i = 1; i <= uptoIndex; i++) {{
            d += (places[i].dist_from_prev_km || 0);
          }}
          if (partialFraction > 0 && uptoIndex + 1 < places.length) {{
            d += (places[uptoIndex + 1].dist_from_prev_km || 0) * partialFraction;
          }}
          return d;
        }}

        function updateHudAtStop(idx) {{
          const p = places[idx];
          stopMarkers.forEach((el, i) => {{
            el.classList.toggle('active', i === idx);
          }});
          const dist = calcCumDist(idx);
          const boba = (dist * 55 / 450).toFixed(1);
          document.getElementById('hud-time').innerText = `${{p.arrive_time}} - ${{p.depart_time}}`;
          document.getElementById('hud-dist').innerText = `${{dist.toFixed(2)}} km`;
          document.getElementById('hud-boba').innerText = boba;
          document.getElementById('bubble-text').innerText = `🎉 第 ${{idx + 1}} 站：${{p.name}} (${{p.must_try_or_see}})`;
          document.getElementById('status-text').innerHTML =
            `抵達 <b>第 ${{idx + 1}} 站：${{p.name}}</b>｜建議停留 ${{p.stay_mins_adjusted}} 分鐘｜亮點：${{p.must_try_or_see}}`;
        }}

        function walkSegment(fromIdx, toIdx, onComplete) {{
          const start = places[fromIdx];
          const end = places[toIdx];
          const sprite = document.getElementById('avatar-sprite');
          sprite.classList.add('avatar-walking');

          const baseDuration = 3200 / speedMultiplier;
          const startTime = performance.now();

          // 計算鏡頭轉向角度
          const dLon = end.lon - start.lon;
          const dLat = end.lat - start.lat;
          const angleDeg = (Math.atan2(dLon, dLat) * 180 / Math.PI);

          if (followCam) {{
            map.easeTo({{
              center: [(start.lon + end.lon) / 2, (start.lat + end.lat) / 2],
              zoom: 15.4,
              pitch: 64,
              bearing: angleDeg,
              duration: baseDuration * 0.85
            }});
          }}

          function animate(now) {{
            if (!isPlaying) {{
              sprite.classList.remove('avatar-walking');
              return;
            }}
            const t = Math.min(1, (now - startTime) / baseDuration);
            // Smoothstep 緩動
            const smoothT = t * t * (3 - 2 * t);
            const curLon = start.lon + (end.lon - start.lon) * smoothT;
            const curLat = start.lat + (end.lat - start.lat) * smoothT;

            travelerMarker.setLngLat([curLon, curLat]);

            // 更新已走過的橘色軌跡
            const walkedCoords = places.slice(0, fromIdx + 1).map(p => [p.lon, p.lat]);
            walkedCoords.push([curLon, curLat]);
            if (map.getSource('route-walked')) {{
              map.getSource('route-walked').setData({{
                type: 'Feature',
                geometry: {{ type: 'LineString', coordinates: walkedCoords }}
              }});
            }}

            const dist = calcCumDist(fromIdx, smoothT);
            document.getElementById('hud-dist').innerText = `${{dist.toFixed(2)}} km`;
            document.getElementById('hud-boba').innerText = (dist * 55 / 450).toFixed(1);
            document.getElementById('bubble-text').innerText =
              `{avatar_emoji} 前往第 ${{toIdx + 1}} 站：${{end.name}} (${{Math.round(smoothT * 100)}}%)`;
            document.getElementById('status-text').innerHTML =
              `移動中：<b>${{start.name}} ➔ ${{end.name}}</b>（距離 ${{end.dist_from_prev_km}} km，約 ${{end.move_mins_from_prev}} 分鐘）`;

            if (t < 1) {{
              animFrame = requestAnimationFrame(animate);
            }} else {{
              sprite.classList.remove('avatar-walking');
              currentIndex = toIdx;
              updateHudAtStop(currentIndex);
              if (followCam) {{
                map.easeTo({{
                  center: [end.lon, end.lat],
                  zoom: 16.0,
                  pitch: 65,
                  duration: 700
                }});
              }}
              setTimeout(() => {{
                if (isPlaying) onComplete();
              }}, 950 / speedMultiplier);
            }}
          }}

          animFrame = requestAnimationFrame(animate);
        }}

        function playLoop() {{
          if (!isPlaying) return;
          if (currentIndex >= places.length - 1) {{
            currentIndex = 0;
            travelerMarker.setLngLat([places[0].lon, places[0].lat]);
            updateHudAtStop(0);
          }}
          walkSegment(currentIndex, currentIndex + 1, () => {{
            if (currentIndex < places.length - 1) {{
              playLoop();
            }} else {{
              isPlaying = false;
              document.getElementById('btn-play').innerText = '🔄 重新漫遊';
              document.getElementById('bubble-text').innerText = '🏁 全程巡禮完成！準備出發囉！';
            }}
          }});
        }}

        function togglePlay() {{
          isPlaying = !isPlaying;
          const btn = document.getElementById('btn-play');
          if (isPlaying) {{
            btn.innerText = '⏸️ 暫停漫遊';
            playLoop();
          }} else {{
            btn.innerText = '▶️ 繼續漫遊';
            if (animFrame) cancelAnimationFrame(animFrame);
            document.getElementById('avatar-sprite').classList.remove('avatar-walking');
          }}
        }}

        function jumpToStop(idx) {{
          isPlaying = false;
          if (animFrame) cancelAnimationFrame(animFrame);
          document.getElementById('btn-play').innerText = '▶️ 自動漫遊';
          document.getElementById('avatar-sprite').classList.remove('avatar-walking');
          currentIndex = idx;
          const p = places[idx];
          travelerMarker.setLngLat([p.lon, p.lat]);
          updateHudAtStop(idx);
          const walkedCoords = places.slice(0, idx + 1).map(pt => [pt.lon, pt.lat]);
          if (map.getSource('route-walked')) {{
            map.getSource('route-walked').setData({{
              type: 'Feature',
              geometry: {{ type: 'LineString', coordinates: walkedCoords }}
            }});
          }}
          map.flyTo({{ center: [p.lon, p.lat], zoom: 16, pitch: 62, duration: 900 }});
        }}

        function stepPrev() {{
          const target = Math.max(0, currentIndex - 1);
          jumpToStop(target);
        }}

        function stepNext() {{
          const target = Math.min(places.length - 1, currentIndex + 1);
          jumpToStop(target);
        }}

        function toggleCameraFollow() {{
          followCam = !followCam;
          document.getElementById('btn-cam').innerText = followCam ? '🎥 視角：跟隨' : '🎥 視角：自由';
        }}

        function changeSpeed() {{
          speedMultiplier = parseFloat(document.getElementById('speed-sel').value || '2');
        }}
      </script>
    </body>
    </html>
    """
  components.html(html_code, height=600)


# ----------------- 點擊按鈕執行分析 -----------------
if start_button:
  if not uploaded_files:
    st.sidebar.warning("請先上傳至少一張截圖，或點擊上方「載入 Demo 行程」！")
  elif not clean_api_key:
    st.sidebar.error("請先輸入您的 Gemini API Key，或直接使用上方免金鑰 Demo！")
  else:
    all_places = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, file in enumerate(uploaded_files):
      status_text.text(
          f"正在分析第 {idx + 1}/{len(uploaded_files)} 張截圖：{file.name} ..."
      )
      places = analyze_image(file)
      if places:
        all_places.extend(places)
      progress_bar.progress((idx + 1) / len(uploaded_files))

    if all_places:
      status_text.text("✅ 分析完成！")
      st.session_state["places"] = all_places
    else:
      status_text.text("⚠️ 未能萃取出景點，請檢查 API Key 或截圖清晰度。")

# ----------------- 畫面展示區 -----------------
if "places" in st.session_state and st.session_state["places"]:
  raw_places = st.session_state["places"]

  # 側邊欄：行程個人化設定
  st.sidebar.markdown("---")
  st.sidebar.subheader("⚙️ 智慧排程與旅遊人格")
  is_optimized = st.sidebar.checkbox("啟用智慧順路排序 (TSP 避免折返跑)", value=True)

  place_names = [
      f"{i+1}. {p.get('name', '未知')}" for i, p in enumerate(raw_places)
  ]
  start_choice = st.sidebar.selectbox(
      "📍 指定第一站起點：", options=range(len(place_names)), format_func=lambda i: place_names[i]
  )

  persona = st.sidebar.radio(
      "🎭 旅遊步調風格：",
      options=[
          "☕ 社畜療癒漫遊 (標準停留)",
          "⚡ 特種兵極速打卡 (停留時間 -30%)",
          "📸 深度慢活出片 (停留時間 +35%)",
      ],
  )
  pace_factor = (
      0.7 if "特種兵" in persona else (1.35 if "深度" in persona else 1.0)
  )

  travel_mode_label = st.sidebar.selectbox(
      "🚇 移動交通方式：",
      options=["🚶 步行漫遊", "🚇 大眾運輸", "🚗 自駕 / 計程車"],
  )
  travel_mode = (
      "walking"
      if "步行" in travel_mode_label
      else ("transit" if "大眾" in travel_mode_label else "driving")
  )

  start_time_obj = st.sidebar.time_input(
      "🕘 預計出發時間：", value=datetime.strptime("09:30", "%H:%M").time()
  )
  start_time_str = start_time_obj.strftime("%H:%M")

  # 執行排序與時間軸計算
  ordered_places = (
      optimize_route(raw_places, start_idx=start_choice)
      if is_optimized
      else list(raw_places)
  )
  enriched_places, summary = enrich_route_metrics(
      ordered_places,
      start_time_str=start_time_str,
      travel_mode=travel_mode,
      pace_factor=pace_factor,
  )

  # 頂部總覽儀表板 (KPI 卡片)
  boba_count = round(summary["calories"] / 450, 1)
  k1, k2, k3, k4 = st.columns(4)
  with k1:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">📍 {len(enriched_places)} 站</div>'
        '<div class="stat-label">今日探索景點數</div></div>',
        unsafe_allow_html=True,
    )
  with k2:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">🛣️ {summary["total_km"]} km</div>'
        f'<div class="stat-label">預估總移動距離（約 {summary["total_move_mins"]} 分鐘）</div></div>',
        unsafe_allow_html=True,
    )
  with k3:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">🕒 {start_time_str} - {summary["end_time"]}</div>'
        '<div class="stat-label">完整行程時間軸</div></div>',
        unsafe_allow_html=True,
    )
  with k4:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">🧋 {boba_count} 杯珍奶</div>'
        f'<div class="stat-label">預計消耗 {summary["calories"]} kcal 熱量指標</div></div>',
        unsafe_allow_html=True,
    )

  st.write("")

  # 頂部動作列：Google Maps 導航 + 行事曆匯出
  act_col1, act_col2, act_col3 = st.columns([2, 1, 1])
  directions_url = generate_google_maps_directions_url(
      enriched_places, travel_mode=travel_mode
  )
  with act_col1:
    if directions_url:
      st.link_button(
          "🗺️ 一鍵開啟 Google Maps 多點順路導航",
          directions_url,
          type="primary",
          use_container_width=True,
      )
  with act_col2:
    ics_data = generate_ics_content(enriched_places)
    st.download_button(
        "📅 匯出手機行事曆 (.ics)",
        data=ics_data,
        file_name="travel_itinerary.ics",
        mime="text/calendar",
        use_container_width=True,
    )
  with act_col3:
    if st.button("➕ 手動新增自訂景點", use_container_width=True):
      st.session_state["show_add_modal"] = not st.session_state.get(
          "show_add_modal", False
      )

  # 手動新增景點表單
  if st.session_state.get("show_add_modal", False):
    with st.expander("➕ 新增自訂順路景點", expanded=True):
      with st.form("add_place_form"):
        f1, f2, f3 = st.columns(3)
        new_name = f1.text_input("地點名稱", placeholder="例如：藍瓶咖啡 京都店")
        new_city = f2.text_input(
            "所在城市",
            value=enriched_places[0].get("city", "日本京都"),
        )
        new_cat = f3.selectbox("類別", ["美食", "景點", "購物", "住宿"])
        f4, f5, f6 = st.columns(3)
        new_note = f4.text_input("推薦看點/必吃", value="順路休息拍照")
        new_lat = f5.number_input(
            "緯度 (Lat)", value=float(enriched_places[-1].get("lat", 25.04))
        )
        new_lon = f6.number_input(
            "經度 (Lon)", value=float(enriched_places[-1].get("lon", 121.51))
        )
        if st.form_submit_button("✅ 加入行程並重新排程"):
          if new_name:
            st.session_state["places"].append({
                "name": new_name,
                "city": new_city,
                "category": new_cat,
                "must_try_or_see": new_note,
                "lat": new_lat,
                "lon": new_lon,
                "stay_mins": 60,
            })
            st.session_state["show_add_modal"] = False
            st.rerun()

  col1, col2 = st.columns([1.05, 1.35])

  # 左欄：智慧時間軸清單
  with col1:
    st.subheader(f"📋 順路時間軸清單（共 {len(enriched_places)} 站）")
    cat_icons = {"美食": "🍜", "景點": "📸", "購物": "🛍️", "住宿": "🏨"}

    for i, p in enumerate(enriched_places, 1):
      if i > 1:
        st.caption(
            f"⬇️ *移動約 {p['dist_from_prev_km']} km（預計 {p['move_mins_from_prev']} 分鐘）*"
        )
      with st.container(border=True):
        c_title, c_del = st.columns([5, 1])
        cat_icon = cat_icons.get(p.get("category", "景點"), "📍")
        c_title.markdown(
            f"#### `{p['arrive_time']} - {p['depart_time']}` 第 {i} 站：{p.get('name', '未知地點')}"
        )
        if len(st.session_state["places"]) > 2:
          if c_del.button("🗑️", key=f"del_{i}", help="移除此站"):
            st.session_state["places"].remove(
                next(
                    item
                    for item in st.session_state["places"]
                    if item.get("name") == p.get("name")
                )
            )
            st.rerun()

        st.write(
            f"{cat_icon} **類別**：{p.get('category', '景點')} ｜ 🏙️ **城市**：{p.get('city', '')} ｜ "
            f"⏱️ **停留**：{p['stay_mins_adjusted']} 分鐘"
        )
        st.write(
            f"💡 **推薦看點/必吃**：{p.get('must_try_or_see', '無')} ｜ 💰 **預估消費**：{p.get('price_est', '依現場為準')}"
        )

        search_text = f"{p.get('name', '')} {p.get('city', '')}".strip()
        single_map_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(search_text)}"
        street_url = (
            f"https://www.google.com/maps/@?api=1&map_action=pano"
            f"&viewpoint={p.get('lat')},{p.get('lon')}"
        )
        st.markdown(
            f"[🔍 Google Maps 店鋪資訊]({single_map_url}) ｜ [👀 開啟實景街景 (Street View)]({street_url})"
        )

    # 旅伴分享文案複製區
    with st.expander("📤 一鍵複製 Line / IG 旅伴分享文案"):
      share_lines = [
          f"✈️ 【{enriched_places[0].get('city', '一日遊')} 順路行程表】",
          f"🕒 時間：{start_time_str} - {summary['end_time']}（總路程 {summary['total_km']} km）\n",
      ]
      for idx, p in enumerate(enriched_places, 1):
        share_lines.append(
            f"{idx}. [{p['arrive_time']}-{p['depart_time']}] {p.get('name')}｜💡{p.get('must_try_or_see')}"
        )
      if directions_url:
        share_lines.append(f"\n🗺️ 完整多點導航：{directions_url}")
      st.code("\n".join(share_lines), language="markdown")

  # 右欄：3D 旅人漫遊地圖 & 2D Folium 切換
  with col2:
    tab_3d, tab_2d = st.tabs([
        "🕹️ 3D 旅人實景漫遊 (支援自動行走/視角跟隨)",
        "🗺️ 2D 經典路線圖 (Folium)",
    ])

    with tab_3d:
      render_3d_walking_map(enriched_places, travel_mode=travel_mode)

    with tab_2d:
      valid_coords = [
          (p.get("lat"), p.get("lon"))
          for p in enriched_places
          if p.get("lat") and p.get("lon")
      ]
      if valid_coords:
        start_lat, start_lon = valid_coords[0]
        m = folium.Map(location=[start_lat, start_lon], zoom_start=14)

        for i, p in enumerate(enriched_places, 1):
          lat, lon = p.get("lat"), p.get("lon")
          if lat and lon:
            popup_content = (
                f"<b>第 {i} 站 ({p['arrive_time']})：{p.get('name')}</b><br>"
                f"{p.get('must_try_or_see')}"
            )
            folium.Marker(
                location=[lat, lon],
                tooltip=f"第 {i} 站：{p.get('name')}",
                popup=folium.Popup(popup_content, max_width=250),
                icon=folium.Icon(
                    color="red" if i == 1 else "blue",
                    icon="flag" if i == 1 else "bookmark",
                    prefix="fa",
                ),
            ).add_to(m)

        if len(valid_coords) > 1:
          folium.PolyLine(
              locations=valid_coords,
              color="#2563EB",
              weight=4,
              opacity=0.85,
              dash_array="6, 8",
          ).add_to(m)

        st_folium(m, width="100%", height=550)
      else:
        st.warning("未能取得有效經緯度座標。")

else:
  st.info(
      "👈 **駭客松評審 Demo 秘訣**：直接點擊左側邊欄的 **「✨ 載入 Demo 行程（立即可玩 3D）」**，"
      "免輸入 API Key、免上傳圖片即可體驗 **3D 旅人漫遊地圖**！若要測試真實 AI 辨識，請輸入 Gemini API Key 並上傳截圖。"
  )