import base64
from datetime import datetime, timedelta
import json
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

# 自訂頂部與導遊講稿視覺樣式
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
    .guide-box {
        background: #f0f9ff;
        border-left: 4px solid #0284c7;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.88rem;
        color: #0c4a6e;
        margin: 6px 0;
    }
    </style>
    <div class="hero-banner">
        <h1>✈️ 上班截圖、下班出發：社畜無腦排行程 AI (3D 實景語音導遊版)</h1>
        <p>IG、小紅書截圖一鍵丟！AI 自動抓出神秘景點、最佳化順路動線，還能讓 3D 分身邊走邊為你語音導覽！</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- 內建駭客松 Demo 範例資料（含 AI 語音導遊講稿） -----------------
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
            "audio_script": (
                "歡迎來到第一站伏見稻荷大社！這裡以綿延山頭的朱紅色千本鳥居聞名，"
                "建議趁早避開人潮，走在鳥居隧道裡拍出夢幻光影，別忘了求一支可愛的狐狸御守喔！"
            ),
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
            "audio_script": (
                "現在抵達世界文化遺產清水寺！整座本堂懸空建在音羽山崖上，完全沒用一根釘子。"
                "站在清水舞台可以遠眺京都市景，下方還有音羽之瀑可以祈求學業、戀愛與長壽。"
            ),
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
            "audio_script": (
                "走了這麼多路，來三年坂的藤菜美休息一下吧！必點師傅現場炙烤的醬油糰子，"
                "外皮微焦酥脆、內裡軟糯，再配上一杯冰涼的洛水無糖抹茶，超級解膩！"
            ),
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
            "audio_script": (
                "傍晚時分來到八坂神社與祇園花見小路！舞殿上掛滿整排贊助商提燈，點燈後非常有京都韻味。"
                "順著石板路漫步，還有機會巧遇前往茶屋的藝伎喔！"
            ),
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
            "audio_script": (
                "最後一站來到鴨川旁的先斗町窄巷！這家柚子元的黃金柚子火鍋果香濃郁、湯頭清甜，"
                "搭配金黃脆皮的柚子胡椒煎餃，為今天的京都順路之旅畫下完美句點！"
            ),
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
            "audio_script": (
                "台北老派約會第一站：大稻埕慈聖宮廟口！坐在百年老榕樹下，"
                "點一碗清甜軟嫩的原汁排骨湯沾辣椒醬油，配上一碗油香十足的古早味高麗菜飯，這就是正港老台北人的早午餐！"
            ),
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
            "audio_script": (
                "吃飽後順路散步到迪化街北段的十連棟！這裡保留了日治時期六大商號相連的巴洛克式紅磚拱廊，"
                "二樓還有空中走廊可以遠眺街景，隨手一拍都是復古大片。"
            ),
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
            "audio_script": (
                "走進迪化街巷弄裡的幻猻家珈琲！老宅磨石子地板配上昏黃燈光非常有質感，"
                "必點他們家帶點大人味微苦焦糖香的招牌布丁，配上一杯自家烘焙的手沖咖啡！"
            ),
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
            "audio_script": (
                "接著來到全台灣最靈驗的霞海城隍廟！喝杯熱甜茶沾沾喜氣、向月老祈求好人緣，"
                "旁邊的永樂市場還有超多台灣印花文創小物可以挖寶。"
            ),
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
            "audio_script": (
                "終點站抵達大稻埕碼頭貨櫃市集！從五號水門走出來就是整片淡水河岸，"
                "在貨櫃屋頂樓點杯精釀啤酒與披薩，吹著晚風欣賞夕陽染紅河面，下班後的社畜靈魂瞬間被治癒！"
            ),
        },
    ],
}

# 預設優先嘗試的模型清單（已移除退役會報 404 的 gemini-1.5-flash，保留原版穩定別名與最新模型）
DEFAULT_MODELS_TO_TRY = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
]


def get_candidate_models(api_key):
  """動態向 Google API 查詢該金鑰帳號實際支援的模型清單，避免寫死模型名稱導致 404。"""
  candidates = list(DEFAULT_MODELS_TO_TRY)
  if not api_key:
    return candidates
  try:
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    res = requests.get(list_url, timeout=8)
    if res.status_code == 200:
      models_info = res.json().get("models", [])
      available = []
      for m in models_info:
        methods = m.get("supportedGenerationMethods", [])
        name = m.get("name", "").replace("models/", "")
        # 篩選支援 generateContent 且屬於 gemini 系列的通用多模態模型
        if "generateContent" in methods and name.startswith("gemini"):
          if not any(
              skip in name
              for skip in ["embedding", "tts", "audio", "imagen", "veo", "robotics", "computer-use"]
          ):
            available.append(name)

      if available:
        # 優先排列 flash / lite 系列模型，確保速度最快、額度最充裕
        prioritized = [m for m in DEFAULT_MODELS_TO_TRY if m in available]
        others = [m for m in available if m not in prioritized]
        others.sort(key=lambda x: (0 if "flash" in x else 1, x))
        return prioritized + others
  except Exception:
    pass
  return candidates


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
    models_to_test = get_candidate_models(clean_api_key)
    success = False
    error_logs = []

    for model_name in models_to_test:
      test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_api_key}"
      payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
      try:
        res = requests.post(test_url, json=payload, timeout=10)
        if res.status_code == 200:
          st.sidebar.success(f"✅ 連線成功！當前可用模型：{model_name}")
          st.session_state["working_model"] = model_name
          success = True
          break
        else:
          err_detail = ""
          try:
            err_detail = res.json().get("error", {}).get("message", "")[:60]
          except Exception:
            err_detail = res.text[:60]
          error_logs.append(f"• {model_name} (HTTP {res.status_code}): {err_detail}")
      except Exception as e:
        error_logs.append(f"• {model_name}: {e}")

    if not success:
      st.sidebar.error(
          "❌ 全部模型連線失敗，請檢查 API Key 是否正確或額度是否已滿：\n"
          + "\n".join(error_logs[:4])
      )

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


# ----------------- 輔助函式：自動生成預設導遊語音講稿 -----------------
def ensure_audio_script(place_dict, idx):
  """若景點沒有 audio_script，動態組合一段自然生動的隨身導遊解說。"""
  script = str(place_dict.get("audio_script") or "").strip()
  if script:
    return script
  name = place_dict.get("name", f"第{idx}站")
  city = place_dict.get("city", "")
  cat = place_dict.get("category", "景點")
  highlight = place_dict.get("must_try_or_see", "招牌特色")
  price = place_dict.get("price_est", "依現場為準")
  return (
      f"現在抵達第 {idx} 站：{city}的{name}！這是一處超人氣的{cat}，"
      f"來到這裡千萬別錯過「{highlight}」，預估花費約 {price}，好好享受這段旅程吧！"
  )


# ----------------- 輔助函式：路徑智慧排序 (TSP 貪婪演算法 + 起點可選) -----------------
def optimize_route(places_list, start_idx=0):
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
        road_dist = round(dist * 1.28, 2)
      else:
        road_dist = 0.8
      move_mins = max(3, int(round((road_dist / speed_kmh) * 60)))
      if travel_mode == "transit":
        move_mins += 6
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
    item["audio_script"] = ensure_audio_script(item, i + 1)
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
    desc = (
        f"推薦亮點：{p.get('must_try_or_see', '')} | "
        f"導遊解說：{p.get('audio_script', '')}"
    )
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


# ----------------- 輔助函式：單站獨立語音播報按鈕 (Web Speech API) -----------------
def render_single_tts_button(script_text, stop_idx, place_name):
  """渲染一個小巧的 HTML5 語音導覽播放按鈕。"""
  safe_text = json.dumps(script_text, ensure_ascii=False)
  safe_title = json.dumps(place_name, ensure_ascii=False)
  btn_html = f"""
    <html>
    <body style="margin:0; padding:0; background:transparent; font-family:sans-serif;">
      <button id="tts-btn-{stop_idx}" onclick="playGuide()" style="
        background: linear-gradient(135deg, #0284c7, #2563eb);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 2px 6px rgba(37,99,235,0.25);
      ">
        🎙️ 聽 AI 導遊解說本站
      </button>
      <script>
        let speaking = false;
        function playGuide() {{
          const btn = document.getElementById('tts-btn-{stop_idx}');
          if (!('speechSynthesis' in window)) {{
            alert('您的瀏覽器不支援語音合成功能');
            return;
          }}
          if (speaking) {{
            window.speechSynthesis.cancel();
            speaking = false;
            btn.innerHTML = '🎙️ 聽 AI 導遊解說本站';
            btn.style.background = 'linear-gradient(135deg, #0284c7, #2563eb)';
            return;
          }}
          window.speechSynthesis.cancel();
          const utter = new SpeechSynthesisUtterance({safe_text});
          utter.lang = 'zh-TW';
          utter.rate = 1.05;
          utter.onend = () => {{
            speaking = false;
            btn.innerHTML = '🎙️ 聽 AI 導遊解說本站';
            btn.style.background = 'linear-gradient(135deg, #0284c7, #2563eb)';
          }};
          speaking = true;
          btn.innerHTML = '⏹️ 停止導覽 (' + {safe_title} + ')';
          btn.style.background = 'linear-gradient(135deg, #ea580c, #dc2626)';
          window.speechSynthesis.speak(utter);
        }}
      </script>
    </body>
    </html>
  """
  components.html(btn_html, height=38)


# ----------------- 核心解析函式（動態探索可用模型 + 備援 REST 呼叫） -----------------
def analyze_image(file_obj):
  image_bytes = file_obj.getvalue()
  mime_type = (
      "image/png" if file_obj.name.lower().endswith(".png") else "image/jpeg"
  )
  encoded_image = base64.b64encode(image_bytes).decode("utf-8")

  prompt = """
    你是一個專業的旅遊行程規劃助手與隨身語音導遊。請分析使用者上傳的這張旅遊/美食/景點截圖，並提取出核心的地點資訊。
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
        "best_time": "建議時段（上午 / 午餐 / 下午茶 / 傍晚 / 晚餐）",
        "audio_script": "50字以內生動活潑的『AI隨身導遊口語解說詞』，像Podcast主持人一樣介紹該站必吃必拍亮點與氛圍"
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
          "temperature": 0.25,
      },
  }

  headers = {"Content-Type": "application/json"}
  errors = []

  models_to_try = get_candidate_models(clean_api_key)
  if st.session_state.get("working_model") in models_to_try:
    wm = st.session_state["working_model"]
    models_to_try = [wm] + [m for m in models_to_try if m != wm]

  for model_name in models_to_try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_api_key}"
    try:
      res = requests.post(url, headers=headers, json=payload, timeout=35)
      if res.status_code == 200:
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        st.session_state["working_model"] = model_name
        return json.loads(text)
      else:
        err_msg = ""
        try:
          err_msg = res.json().get("error", {}).get("message", "")[:60]
        except Exception:
          err_msg = res.text[:60]
        errors.append(f"{model_name} (HTTP {res.status_code}: {err_msg})")
    except Exception as e:
      errors.append(f"{model_name} ({e})")

  st.error("所有備援模型皆呼叫失敗：\n" + "\n".join(errors[:5]))
  return []


# ----------------- 3D 旅人漫遊地圖組件 (Leaflet 核心 + CSS 3D 立體透視 + AI 隨身語音導遊) -----------------
def render_3d_walking_map(enriched_places, travel_mode="walking"):
  """使用與 Folium 相同、100% 支援 Streamlit iframe 的 Leaflet 圖磚引擎，結合 CSS3 3D 透視傾斜舞台與直立 3D 旅人動畫。"""
  valid_places = [
      dict(p)
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
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css" />
      <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 0;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: transparent;
        }}
        #viewport {{
          position: relative;
          width: 100%;
          height: 610px;
          border-radius: 18px;
          overflow: hidden;
          background: linear-gradient(180deg, #0f172a 0%, #1e3a8a 26%, #bae6fd 52%, #e2e8f0 100%);
          box-shadow: 0 14px 30px rgba(15, 23, 42, 0.22);
          border: 1px solid #cbd5e1;
          perspective: 950px;
        }}

        /* 3D 傾斜地圖舞台 */
        #map-stage {{
          position: absolute;
          top: -22%;
          left: -22%;
          width: 144%;
          height: 144%;
          transform-origin: 50% 55%;
          transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
        }}
        #map-stage.tilted-3d {{
          transform: rotateX(48deg) scale(1.06);
        }}
        #map-stage.flat-2d {{
          transform: rotateX(0deg) scale(0.72);
        }}

        #leaflet-map {{
          width: 100%;
          height: 100%;
          background: #dbeafe;
        }}

        /* 遠景大氣霧化遮罩 */
        .horizon-fog {{
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 115px;
          background: linear-gradient(180deg, rgba(15, 23, 42, 0.78) 0%, rgba(30, 58, 138, 0.28) 55%, rgba(255, 255, 255, 0) 100%);
          pointer-events: none;
          z-index: 400;
        }}

        /* 頂部 RPG 狀態與 AI 導遊字幕列 */
        .hud-top {{
          position: absolute;
          top: 12px;
          left: 12px;
          right: 12px;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 10px;
          pointer-events: none;
          z-index: 800;
        }}
        .hud-badge {{
          background: rgba(15, 23, 42, 0.88);
          backdrop-filter: blur(8px);
          color: #f8fafc;
          padding: 10px 15px;
          border-radius: 12px;
          font-size: 13px;
          box-shadow: 0 4px 15px rgba(0,0,0,0.28);
          border: 1px solid rgba(255,255,255,0.16);
          pointer-events: auto;
          max-width: 65%;
        }}
        .hud-badge strong {{
          color: #38bdf8;
          font-size: 14px;
        }}
        .guide-subtitle {{
          margin-top: 5px;
          padding-top: 5px;
          border-top: 1px solid rgba(255,255,255,0.16);
          color: #fde047;
          font-size: 12.5px;
          line-height: 1.4;
        }}

        /* 底部播放與語音導覽控制面板 */
        .control-bar {{
          position: absolute;
          bottom: 14px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(15, 23, 42, 0.92);
          backdrop-filter: blur(10px);
          padding: 9px 14px;
          border-radius: 999px;
          display: flex;
          align-items: center;
          gap: 7px;
          z-index: 800;
          box-shadow: 0 8px 25px rgba(0,0,0,0.38);
          border: 1px solid rgba(255,255,255,0.2);
          color: white;
          white-space: nowrap;
        }}
        .ctrl-btn {{
          background: #2563eb;
          color: white;
          border: none;
          padding: 7px 12px;
          border-radius: 999px;
          font-size: 12.5px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
        }}
        .ctrl-btn:hover {{ background: #1d4ed8; transform: translateY(-1px); }}
        .ctrl-btn.secondary {{ background: #334155; }}
        .ctrl-btn.secondary:hover {{ background: #475569; }}
        .ctrl-btn.voice-on {{ background: #059669; }}
        .ctrl-btn.voice-on:hover {{ background: #047857; }}
        .speed-select {{
          background: #1e293b;
          color: #e2e8f0;
          border: 1px solid #475569;
          border-radius: 8px;
          padding: 5px 7px;
          font-size: 12px;
          cursor: pointer;
        }}

        /* 螢幕空間直立 3D 旅人覆蓋層 */
        #avatar-overlay {{
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 650;
          overflow: hidden;
        }}
        .traveler-screen-node {{
          position: absolute;
          width: 76px;
          height: 94px;
          transform: translate(-50%, -88%);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: flex-end;
          pointer-events: none;
          will-change: left, top;
        }}
        .speech-bubble {{
          position: absolute;
          bottom: 84px;
          background: #ffffff;
          color: #0f172a;
          padding: 7px 12px;
          border-radius: 12px;
          font-size: 12.5px;
          font-weight: 800;
          white-space: nowrap;
          box-shadow: 0 8px 20px rgba(15, 23, 42, 0.28);
          border: 2px solid #2563eb;
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
          width: 58px;
          height: 64px;
          position: relative;
          transform-origin: bottom center;
          filter: drop-shadow(0 6px 8px rgba(15, 23, 42, 0.35));
        }}
        .avatar-walking {{
          animation: walk-bounce 0.38s infinite alternate ease-in-out;
        }}
        @keyframes walk-bounce {{
          0% {{ transform: translateY(0px) rotate(-6deg) scale(1.02); }}
          100% {{ transform: translateY(-11px) rotate(6deg) scale(1.08); }}
        }}
        .avatar-shadow {{
          width: 38px;
          height: 12px;
          background: rgba(15, 23, 42, 0.48);
          border-radius: 50%;
          filter: blur(2px);
          margin-top: -5px;
        }}

        /* 站點 3D 立柱地標樣式 */
        .stop-pin-wrapper {{
          background: transparent;
          border: none;
        }}
        .stop-pin {{
          display: inline-block;
          background: linear-gradient(135deg, #1d4ed8, #0284c7);
          color: white;
          font-weight: 800;
          font-size: 12px;
          padding: 5px 10px;
          border-radius: 999px;
          border: 2px solid white;
          box-shadow: 0 6px 12px rgba(15, 23, 42, 0.4);
          white-space: nowrap;
          transform: translate(-50%, -100%);
          cursor: pointer;
          transition: all 0.2s ease;
        }}
        .stop-pin.active {{
          background: linear-gradient(135deg, #f59e0b, #dc2626);
          transform: translate(-50%, -110%) scale(1.18);
          z-index: 999;
        }}
        .stop-stem {{
          width: 4px;
          height: 14px;
          background: #ffffff;
          margin: -2px auto 0 auto;
          border-radius: 2px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.4);
        }}
      </style>
    </head>
    <body>
      <div id="viewport">
        <!-- 3D 傾斜地圖舞台 -->
        <div id="map-stage" class="tilted-3d">
          <div id="leaflet-map"></div>
        </div>

        <div class="horizon-fog"></div>

        <!-- 直立 3D 旅人覆蓋層 -->
        <div id="avatar-overlay">
          <div class="traveler-screen-node" id="traveler-node">
            <div class="speech-bubble" id="bubble-text">📍 第 1 站：載入中...</div>
            <div class="avatar-body" id="avatar-sprite">
              <svg viewBox="0 0 64 72" width="58" height="64">
                <rect x="8" y="25" width="13" height="23" rx="5" fill="#ea580c" stroke="#fff" stroke-width="2"/>
                <rect x="17" y="24" width="27" height="26" rx="9" fill="#2563eb" stroke="#fff" stroke-width="2.5"/>
                <path d="M22 25 L22 46" stroke="#fde047" stroke-width="3" stroke-linecap="round"/>
                <circle cx="32" cy="14" r="11.5" fill="#fde68a" stroke="#fff" stroke-width="2.5"/>
                <rect x="25" y="10" width="17" height="6" rx="3" fill="#0f172a"/>
                <rect x="20" y="48" width="8.5" height="15" rx="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>
                <rect x="33" y="48" width="8.5" height="15" rx="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>
              </svg>
            </div>
            <div class="avatar-shadow"></div>
          </div>
        </div>

        <!-- 頂部 HUD 導覽列 -->
        <div class="hud-top">
          <div class="hud-badge" id="status-box">
            <strong>🕹️ 3D 實景預演 & AI 隨身語音導遊</strong><br/>
            <span id="status-text">點擊下方「▶️ 自動漫遊」，3D 旅人每走到一站會自動語音播報導覽！</span>
            <div class="guide-subtitle" id="guide-caption">🎙️ 導遊字幕：準備出發！</div>
          </div>
          <div class="hud-badge" style="text-align:right; max-width:33%;">
            <div>🕒 時段：<strong id="hud-time">--:--</strong></div>
            <div>👟 路程：<strong id="hud-dist">0.00 km</strong> (<span id="hud-boba">0.0</span> 杯珍奶🧋)</div>
          </div>
        </div>

        <!-- 底部控制列 -->
        <div class="control-bar">
          <button class="ctrl-btn" id="btn-play" onclick="togglePlay()">▶️ 自動漫遊</button>
          <button class="ctrl-btn secondary" onclick="stepPrev()" title="上一站">⏮️</button>
          <button class="ctrl-btn secondary" onclick="stepNext()" title="下一站">⏭️</button>
          <button class="ctrl-btn voice-on" id="btn-voice" onclick="toggleVoice()">🔊 語音：開</button>
          <button class="ctrl-btn secondary" onclick="speakCurrentStop()">🎙️ 重聽</button>
          <button class="ctrl-btn secondary" id="btn-tile" onclick="switchTileLayer()">🛰️ 切換衛星圖</button>
          <button class="ctrl-btn secondary" id="btn-tilt" onclick="toggleTilt()">📐 3D 視角</button>
          <select class="speed-select" id="speed-sel" onchange="changeSpeed()">
            <option value="1">1x</option>
            <option value="2" selected>2x</option>
            <option value="4">4x</option>
          </select>
        </div>
      </div>

      <script>
        const places = {places_json};
        let currentIndex = 0;
        let isPlaying = false;
        let voiceEnabled = true;
        let isTilted3D = true;
        let currentTileMode = 'street';
        let speedMultiplier = 2;
        let animFrame = null;
        let currentLat = places[0].lat;
        let currentLon = places[0].lon;

        const map = L.map('leaflet-map', {{
          center: [places[0].lat, places[0].lon],
          zoom: 15,
          zoomControl: false,
          attributionControl: false
        }});

        const tileLayers = {{
          street: L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}&hl=zh-TW', {{
            maxZoom: 20
          }}),
          satellite: L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={{x}}&y={{y}}&z={{z}}&hl=zh-TW', {{
            maxZoom: 20
          }}),
          osm: L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19
          }})
        }};

        let activeLayer = tileLayers.street;
        activeLayer.on('tileerror', function() {{
          if (activeLayer !== tileLayers.osm) {{
            map.removeLayer(activeLayer);
            activeLayer = tileLayers.osm;
            activeLayer.addTo(map);
          }}
        }});
        activeLayer.addTo(map);

        const allLatLngs = places.map(p => [p.lat, p.lon]);
        L.polyline(allLatLngs, {{
          color: '#38bdf8',
          weight: 10,
          opacity: 0.45,
          lineCap: 'round'
        }}).addTo(map);

        L.polyline(allLatLngs, {{
          color: '#2563eb',
          weight: 5,
          dashArray: '10, 8',
          opacity: 0.9
        }}).addTo(map);

        const walkedPolyline = L.polyline([[places[0].lat, places[0].lon]], {{
          color: '#f59e0b',
          weight: 7,
          opacity: 0.98,
          lineCap: 'round'
        }}).addTo(map);

        const pinElements = [];
        places.forEach((p, idx) => {{
          const iconHtml = `
            <div class="stop-pin ${{idx === 0 ? 'active' : ''}}" id="pin-badge-${{idx}}">
              ${{idx + 1}}. ${{p.name}}
              <div class="stop-stem"></div>
            </div>
          `;
          const customIcon = L.divIcon({{
            className: 'stop-pin-wrapper',
            html: iconHtml,
            iconSize: [0, 0],
            iconAnchor: [0, 0]
          }});
          const marker = L.marker([p.lat, p.lon], {{ icon: customIcon }}).addTo(map);
          marker.on('click', () => {{
            jumpToStop(idx);
            speakStopGuide(idx, null);
          }});
          pinElements.push(marker);
        }});

        function syncTravelerScreenPosition() {{
          const stage = document.getElementById('map-stage');
          const viewport = document.getElementById('viewport');
          const pt = map.latLngToContainerPoint([currentLat, currentLon]);

          let probe = document.getElementById('coord-probe');
          if (!probe) {{
            probe = document.createElement('div');
            probe.id = 'coord-probe';
            probe.style.position = 'absolute';
            probe.style.width = '2px';
            probe.style.height = '2px';
            probe.style.pointerEvents = 'none';
            stage.appendChild(probe);
          }}
          probe.style.left = pt.x + 'px';
          probe.style.top = pt.y + 'px';

          const probeRect = probe.getBoundingClientRect();
          const viewRect = viewport.getBoundingClientRect();

          const screenX = probeRect.left - viewRect.left;
          const screenY = probeRect.top - viewRect.top;

          const node = document.getElementById('traveler-node');
          node.style.left = screenX + 'px';
          node.style.top = screenY + 'px';
        }}

        map.on('move zoom viewreset resize', syncTravelerScreenPosition);
        window.addEventListener('resize', () => {{
          map.invalidateSize();
          syncTravelerScreenPosition();
        }});

        function speakStopGuide(idx, onDoneCallback) {{
          const p = places[idx];
          const scriptText = p.audio_script || (`抵達第 ${{idx + 1}} 站 ${{p.name}}，推薦必看：${{p.must_try_or_see}}`);
          document.getElementById('guide-caption').innerText = `🎙️ AI 導遊：「${{scriptText}}」`;

          if (!voiceEnabled || !('speechSynthesis' in window)) {{
            if (onDoneCallback) setTimeout(onDoneCallback, 1100 / speedMultiplier);
            return;
          }}

          window.speechSynthesis.cancel();
          const utter = new SpeechSynthesisUtterance(scriptText);
          utter.lang = 'zh-TW';
          utter.rate = Math.min(1.35, 1.0 + (speedMultiplier - 1) * 0.12);
          utter.onend = () => {{
            if (onDoneCallback) onDoneCallback();
          }};
          utter.onerror = () => {{
            if (onDoneCallback) onDoneCallback();
          }};
          window.speechSynthesis.speak(utter);
        }}

        function speakCurrentStop() {{
          speakStopGuide(currentIndex, null);
        }}

        function toggleVoice() {{
          voiceEnabled = !voiceEnabled;
          const btn = document.getElementById('btn-voice');
          if (voiceEnabled) {{
            btn.innerText = '🔊 語音：開';
            btn.classList.add('voice-on');
            btn.classList.remove('secondary');
            speakCurrentStop();
          }} else {{
            window.speechSynthesis.cancel();
            btn.innerText = '🔇 語音：關';
            btn.classList.remove('voice-on');
            btn.classList.add('secondary');
          }}
        }}

        function switchTileLayer() {{
          map.removeLayer(activeLayer);
          const btn = document.getElementById('btn-tile');
          if (currentTileMode === 'street') {{
            currentTileMode = 'satellite';
            activeLayer = tileLayers.satellite;
            btn.innerText = '🗺️ 切換街道圖';
          }} else {{
            currentTileMode = 'street';
            activeLayer = tileLayers.street;
            btn.innerText = '🛰️ 切換衛星圖';
          }}
          activeLayer.addTo(map);
        }}

        function toggleTilt() {{
          isTilted3D = !isTilted3D;
          const stage = document.getElementById('map-stage');
          const btn = document.getElementById('btn-tilt');
          if (isTilted3D) {{
            stage.className = 'tilted-3d';
            btn.innerText = '📐 3D 視角';
          }} else {{
            stage.className = 'flat-2d';
            btn.innerText = '🗺️ 平面視角';
          }}
          setTimeout(syncTravelerScreenPosition, 50);
          setTimeout(syncTravelerScreenPosition, 350);
          setTimeout(syncTravelerScreenPosition, 620);
        }}

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
          places.forEach((_, i) => {{
            const badge = document.getElementById(`pin-badge-${{i}}`);
            if (badge) badge.classList.toggle('active', i === idx);
          }});
          const dist = calcCumDist(idx);
          const boba = (dist * 55 / 450).toFixed(1);
          document.getElementById('hud-time').innerText = `${{p.arrive_time}} - ${{p.depart_time}}`;
          document.getElementById('hud-dist').innerText = `${{dist.toFixed(2)}} km`;
          document.getElementById('hud-boba').innerText = boba;
          document.getElementById('bubble-text').innerText = `🎉 第 ${{idx + 1}} 站：${{p.name}} (${{p.must_try_or_see}})`;
          document.getElementById('status-text').innerHTML =
            `抵達 <b>第 ${{idx + 1}} 站：${{p.name}}</b>｜停留 ${{p.stay_mins_adjusted}} 分鐘｜亮點：${{p.must_try_or_see}}`;
          document.getElementById('guide-caption').innerText = `🎙️ AI 導遊：「${{p.audio_script || p.must_try_or_see}}」`;
        }}

        function walkSegment(fromIdx, toIdx, onComplete) {{
          const start = places[fromIdx];
          const end = places[toIdx];
          const sprite = document.getElementById('avatar-sprite');
          sprite.classList.add('avatar-walking');

          const baseDuration = 3000 / speedMultiplier;
          const startTime = performance.now();

          function animate(now) {{
            if (!isPlaying) {{
              sprite.classList.remove('avatar-walking');
              return;
            }}
            const t = Math.min(1, (now - startTime) / baseDuration);
            const smoothT = t * t * (3 - 2 * t);
            currentLat = start.lat + (end.lat - start.lat) * smoothT;
            currentLon = start.lon + (end.lon - start.lon) * smoothT;

            map.panTo([currentLat, currentLon], {{ animate: false }});
            syncTravelerScreenPosition();

            const walkedCoords = places.slice(0, fromIdx + 1).map(p => [p.lat, p.lon]);
            walkedCoords.push([currentLat, currentLon]);
            walkedPolyline.setLatLngs(walkedCoords);

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
              currentLat = end.lat;
              currentLon = end.lon;
              map.panTo([currentLat, currentLon], {{ animate: true, duration: 0.4 }});
              syncTravelerScreenPosition();
              updateHudAtStop(currentIndex);

              speakStopGuide(currentIndex, () => {{
                if (isPlaying) onComplete();
              }});
            }}
          }}

          animFrame = requestAnimationFrame(animate);
        }}

        function playLoop() {{
          if (!isPlaying) return;
          if (currentIndex >= places.length - 1) {{
            currentIndex = 0;
            currentLat = places[0].lat;
            currentLon = places[0].lon;
            map.panTo([currentLat, currentLon], {{ animate: false }});
            walkedPolyline.setLatLngs([[currentLat, currentLon]]);
            syncTravelerScreenPosition();
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
            if (currentIndex === 0) {{
              speakStopGuide(0, () => {{
                if (isPlaying) playLoop();
              }});
            }} else {{
              playLoop();
            }}
          }} else {{
            btn.innerText = '▶️ 繼續漫遊';
            if (animFrame) cancelAnimationFrame(animFrame);
            window.speechSynthesis.cancel();
            document.getElementById('avatar-sprite').classList.remove('avatar-walking');
          }}
        }}

        function jumpToStop(idx) {{
          isPlaying = false;
          if (animFrame) cancelAnimationFrame(animFrame);
          window.speechSynthesis.cancel();
          document.getElementById('btn-play').innerText = '▶️ 自動漫遊';
          document.getElementById('avatar-sprite').classList.remove('avatar-walking');
          currentIndex = idx;
          const p = places[idx];
          currentLat = p.lat;
          currentLon = p.lon;
          map.setView([currentLat, currentLon], 15, {{ animate: true }});
          const walkedCoords = places.slice(0, idx + 1).map(pt => [pt.lat, pt.lon]);
          walkedPolyline.setLatLngs(walkedCoords);
          syncTravelerScreenPosition();
          updateHudAtStop(idx);
        }}

        function stepPrev() {{
          const target = Math.max(0, currentIndex - 1);
          jumpToStop(target);
          speakStopGuide(target, null);
        }}

        function stepNext() {{
          const target = Math.min(places.length - 1, currentIndex + 1);
          jumpToStop(target);
          speakStopGuide(target, null);
        }}

        function changeSpeed() {{
          speedMultiplier = parseFloat(document.getElementById('speed-sel').value || '2');
        }}

        setTimeout(() => {{
          map.invalidateSize();
          syncTravelerScreenPosition();
          updateHudAtStop(0);
        }}, 120);
      </script>
    </body>
    </html>
    """
  components.html(html_code, height=625)


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
      "📍 指定第一站起點：",
      options=range(len(place_names)),
      format_func=lambda i: place_names[i],
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

  total_stops = len(enriched_places)

  # 頂部總覽儀表板 (4 張 KPI 卡片)
  boba_count = round(summary["calories"] / 450, 1)
  k1, k2, k3, k4 = st.columns(4)
  with k1:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">📍 {total_stops} 站</div>'
        '<div class="stat-label">今日探索景點數</div></div>',
        unsafe_allow_html=True,
    )
  with k2:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">🛣️ {summary["total_km"]} km</div>'
        f'<div class="stat-label">總移動距離（約 {summary["total_move_mins"]} 分鐘）</div></div>',
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
        f'<div class="stat-label">預計消耗 {summary["calories"]} kcal</div></div>',
        unsafe_allow_html=True,
    )

  st.write("")

  # 頂部動作列：Google Maps 導航 + 行事曆匯出 + 新增景點
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

  # 左欄：智慧時間軸清單（含 AI 隨身語音導遊）
  with col1:
    st.subheader(f"📋 順路時間軸 & 隨身語音導覽（共 {total_stops} 站）")
    cat_icons = {"美食": "🍜", "景點": "📸", "購物": "🛍️", "住宿": "🏨"}

    for i, p in enumerate(enriched_places, 1):
      p_name = p.get("name", f"第{i}站")

      if i > 1:
        st.caption(
            f"⬇️ *移動約 {p['dist_from_prev_km']} km（預計 {p['move_mins_from_prev']} 分鐘）*"
        )
      with st.container(border=True):
        c_title, c_del = st.columns([5, 1])
        cat_icon = cat_icons.get(p.get("category", "景點"), "📍")
        c_title.markdown(
            f"#### `{p['arrive_time']} - {p['depart_time']}` 第 {i} 站：{p_name}"
        )

        if len(st.session_state["places"]) > 2:
          if c_del.button("🗑️", key=f"del_{i}", help="移除此站"):
            st.session_state["places"].remove(
                next(
                    item
                    for item in st.session_state["places"]
                    if item.get("name") == p_name
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

        # AI 隨身語音導遊講稿區 + 單站試聽按鈕
        st.markdown(
            f'<div class="guide-box">🎙️ <b>AI 導遊解說：</b>「{p["audio_script"]}」</div>',
            unsafe_allow_html=True,
        )
        render_single_tts_button(p["audio_script"], i, p_name)

        search_text = f"{p_name} {p.get('city', '')}".strip()
        single_map_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(search_text)}"
        street_url = (
            f"https://www.google.com/maps/@?api=1&map_action=pano"
            f"&viewpoint={p.get('lat')},{p.get('lon')}"
        )
        st.markdown(
            f"[🔍 Google Maps 店鋪資訊]({single_map_url}) ｜ [👀 開啟 360° 實景街景 (Street View)]({street_url})"
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

  # 右欄：3D 旅人語音漫遊 & 2D Folium 切換
  with col2:
    tab_3d, tab_2d = st.tabs([
        "🕹️ 3D 旅人實景漫遊 + AI 語音導遊",
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
      "免輸入 API Key、免上傳圖片即可體驗 **3D 旅人漫遊與 AI 隨身語音導遊**！"
  )