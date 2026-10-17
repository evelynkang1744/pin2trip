import base64
from datetime import datetime, timedelta
import io
import json
import urllib.parse
import folium
from geopy.distance import geodesic
from PIL import Image, ImageDraw, ImageFont
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

# 自訂頂部與集章卡視覺樣式
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
    /* 集章卡視覺樣式 */
    .stamp-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
        gap: 12px;
        margin-top: 10px;
        margin-bottom: 14px;
    }
    .stamp-slot {
        background: #fffbeb;
        border: 2px dashed #d97706;
        border-radius: 14px;
        padding: 12px 10px;
        text-align: center;
        position: relative;
        transition: all 0.2s ease;
    }
    .stamp-slot.done {
        background: #fef2f2;
        border: 2px solid #dc2626;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.12);
    }
    .stamp-seal {
        width: 64px;
        height: 64px;
        margin: 0 auto 6px auto;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 12px;
        line-height: 1.15;
    }
    .stamp-seal.locked {
        border: 2px dashed #94a3b8;
        color: #94a3b8;
        background: #f8fafc;
    }
    .stamp-seal.unlocked {
        border: 3px double #dc2626;
        color: #dc2626;
        background: rgba(254, 226, 226, 0.65);
        transform: rotate(-10deg);
        box-shadow: inset 0 0 0 2px rgba(220, 38, 38, 0.25);
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
        <h1>✈️ 上班截圖、下班出發：社畜無腦排行程 AI (3D 語音導遊 & 集章版)</h1>
        <p>IG、小紅書截圖一鍵丟！AI 自動抓出神秘景點、最佳化順路動線，支援 3D 分身漫遊、隨身語音導遊與踩點集章海報！</p>
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

# 備援模型清單
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

# 初始化打卡狀態與照片紀錄
if "checked_places" not in st.session_state:
  st.session_state["checked_places"] = set()
if "checkin_photos" not in st.session_state:
  st.session_state["checkin_photos"] = {}

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
  st.session_state["checked_places"] = set()
  st.session_state["checkin_photos"] = {}
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


# ----------------- 輔助函式：自動生成預設導遊語音講稿 -----------------
def ensure_audio_script(place_dict, idx):
  """若景點沒有 audio_script，動態組合一段自然生動的隨身導遊解說。"""
  script = place_dict.get("audio_script", "").strip()
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


# ----------------- 輔助函式：Pillow 動態合成「今日制霸集章紀念海報」 -----------------
def load_cjk_font(size):
  """自動尋找系統可用的中日韓字型，確保海報中文不亂碼。"""
  font_candidates = [
      "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
      "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
      "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
      "/System/Library/Fonts/PingFang.ttc",
      "/System/Library/Fonts/STHeiti Light.ttc",
      "C:/Windows/Fonts/msjhbd.ttc",
      "C:/Windows/Fonts/msjh.ttc",
      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
  ]
  for path in font_candidates:
    try:
      return ImageFont.truetype(path, size)
    except Exception:
      continue
  return ImageFont.load_default()


def generate_stamp_poster_png(
    enriched_places, summary, checked_set, photos_dict
):
  """使用 Pillow 繪製精美拍立得風格的『打卡集章紀念海報』並回傳 PNG bytes。"""
  n = len(enriched_places)
  width = 880
  row_h = 128
  height = 280 + n * row_h + 110

  img = Image.new("RGB", (width, height), (253, 250, 243))
  draw = ImageDraw.Draw(img)

  font_title = load_cjk_font(32)
  font_sub = load_cjk_font(18)
  font_card_title = load_cjk_font(22)
  font_body = load_cjk_font(16)
  font_stamp = load_cjk_font(18)

  # 頂部深藍漸層橫幅
  draw.rectangle([(0, 0), (width, 165)], fill=(15, 23, 42))
  draw.rectangle([(0, 158), (width, 165)], fill=(245, 158, 11))

  city_title = enriched_places[0].get("city", "精選旅遊") if enriched_places else "旅遊"
  today_disp = datetime.now().strftime("%Y.%m.%d")
  draw.text(
      (36, 28),
      f"✈️ {city_title}・順路制霸集章紀念卡",
      fill=(255, 255, 255),
      font=font_title,
  )
  boba_cnt = round(summary["calories"] / 450, 1)
  draw.text(
      (36, 78),
      f"📅 日期：{today_disp}   ｜   🛣️ 總路程：{summary['total_km']} km   ｜   🧋 消耗熱量：{summary['calories']} kcal ({boba_cnt} 杯珍奶)",
      fill=(186, 230, 253),
      font=font_sub,
  )
  done_cnt = sum(1 for p in enriched_places if p.get("name") in checked_set)
  draw.text(
      (36, 114),
      f"💮 集章進度：已解鎖 {done_cnt} / {n} 站   （{'🎉 全程完美制霸！' if done_cnt == n else '持續探索中！'}）",
      fill=(253, 224, 71),
      font=font_sub,
  )

  # 繪製每一站卡片與印章
  y_cursor = 195
  for idx, p in enumerate(enriched_places, 1):
    name = p.get("name", f"第{idx}站")
    is_checked = name in checked_set

    card_bg = (255, 245, 245) if is_checked else (255, 255, 255)
    border_col = (220, 38, 38) if is_checked else (203, 213, 225)
    draw.rounded_rectangle(
        [(36, y_cursor), (width - 36, y_cursor + row_h - 16)],
        radius=16,
        fill=card_bg,
        outline=border_col,
        width=3 if is_checked else 2,
    )

    # 左側站別編號圓章
    cx, cy = 84, y_cursor + (row_h - 16) // 2
    circle_col = (220, 38, 38) if is_checked else (37, 99, 235)
    draw.ellipse([(cx - 26, cy - 26), (cx + 26, cy + 26)], fill=circle_col)
    draw.text((cx - 14, cy - 13), f"0{idx}", fill=(255, 255, 255), font=font_card_title)

    # 中間景點文字
    draw.text(
        (130, y_cursor + 16),
        f"[{p['arrive_time']} - {p['depart_time']}]  {name}",
        fill=(15, 23, 42),
        font=font_card_title,
    )
    draw.text(
        (130, y_cursor + 52),
        f"🏷️ {p.get('category', '景點')}  ｜  💡 必看亮點：{p.get('must_try_or_see', '')}",
        fill=(71, 85, 105),
        font=font_body,
    )
    draw.text(
        (130, y_cursor + 80),
        f"🎙️ 導遊小記：{p.get('audio_script', '')[:34]}...",
        fill=(3, 105, 161),
        font=font_body,
    )

    # 若有上傳打卡照片，縮圖貼在右側印章旁
    if name in photos_dict and photos_dict[name]:
      try:
        user_img = Image.open(io.BytesIO(photos_dict[name])).convert("RGB")
        user_img.thumbnail((84, 84))
        px = width - 255
        py = y_cursor + 14
        draw.rectangle(
            [(px - 4, py - 4), (px + user_img.width + 4, py + user_img.height + 4)],
            fill=(255, 255, 255),
            outline=(203, 213, 225),
            width=2,
        )
        img.paste(user_img, (px, py))
      except Exception:
        pass

    # 右側日本車站風紀念印章
    sx, sy = width - 105, y_cursor + (row_h - 16) // 2
    if is_checked:
      draw.ellipse(
          [(sx - 40, sy - 40), (sx + 40, sy + 40)],
          outline=(220, 38, 38),
          width=4,
      )
      draw.ellipse(
          [(sx - 34, sy - 34), (sx + 34, sy + 34)],
          outline=(220, 38, 38),
          width=1,
      )
      draw.text((sx - 26, sy - 20), "💮已踩點", fill=(220, 38, 38), font=font_stamp)
      draw.text((sx - 24, sy + 4), "PASS!", fill=(220, 38, 38), font=font_body)
    else:
      draw.ellipse(
          [(sx - 38, sy - 38), (sx + 38, sy + 38)],
          outline=(148, 163, 184),
          width=2,
      )
      draw.text((sx - 26, sy - 10), "待解鎖", fill=(148, 163, 184), font=font_stamp)

    y_cursor += row_h

  # 底部簽名欄
  draw.text(
      (36, height - 55),
      "Generated by 截圖轉行程 Travel Pin-to-Itinerary AI ｜ 上班截圖、下班出發！",
      fill=(100, 116, 139),
      font=font_body,
  )

  buf = io.BytesIO()
  img.save(buf, format="PNG")
  return buf.getvalue()


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


# ----------------- 核心解析函式（多模型動態備援 REST 呼叫 + 產出語音導覽講稿） -----------------
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


# ----------------- 3D 旅人漫遊地圖組件 (MapLibre 3D + 動畫角色 + AI 隨身語音導遊) -----------------
def render_3d_walking_map(enriched_places, checked_set, travel_mode="walking"):
  """使用 MapLibre GL JS 建立 62 度傾斜 3D 立體地圖、行走小人與 Web Speech 隨身語音導遊。"""
  valid_places = []
  for p in enriched_places:
    if p.get("lat") is not None and p.get("lon") is not None:
      item = dict(p)
      item["is_checked"] = item.get("name") in checked_set
      valid_places.append(item)

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
          height: 610px;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
          border: 1px solid #cbd5e1;
        }}
        #map {{ width: 100%; height: 100%; }}

        /* 頂部 RPG 狀態資訊列 */
        .hud-top {{
          position: absolute;
          top: 12px;
          left: 12px;
          right: 52px;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 10px;
          pointer-events: none;
          z-index: 10;
        }}
        .hud-badge {{
          background: rgba(15, 23, 42, 0.88);
          backdrop-filter: blur(8px);
          color: #f8fafc;
          padding: 10px 15px;
          border-radius: 12px;
          font-size: 13px;
          box-shadow: 0 4px 15px rgba(0,0,0,0.25);
          border: 1px solid rgba(255,255,255,0.15);
          pointer-events: auto;
          max-width: 62%;
        }}
        .hud-badge strong {{
          color: #38bdf8;
          font-size: 14px;
        }}
        .guide-subtitle {{
          margin-top: 5px;
          padding-top: 5px;
          border-top: 1px solid rgba(255,255,255,0.15);
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
          gap: 8px;
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
          padding: 7px 13px;
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
        .stop-pin.stamped {{
          background: linear-gradient(135deg, #dc2626, #be123c);
          border: 2px solid #fef08a;
        }}
      </style>
    </head>
    <body>
      <div id="map-wrapper">
        <div id="map"></div>

        <div class="hud-top">
          <div class="hud-badge" id="status-box">
            <strong>🕹️ 3D 實景預演 & AI 隨身語音導遊</strong><br/>
            <span id="status-text">點擊下方「▶️ 自動漫遊」，3D 旅人每走到一站會自動語音播報導覽！</span>
            <div class="guide-subtitle" id="guide-caption">🎙️ 導遊字幕：準備出發！</div>
          </div>
          <div class="hud-badge" style="text-align:right; max-width:34%;">
            <div>🕒 時段：<strong id="hud-time">--:--</strong></div>
            <div>👟 路程：<strong id="hud-dist">0.00 km</strong> (<span id="hud-boba">0.0</span> 杯珍奶🧋)</div>
          </div>
        </div>

        <div class="control-bar">
          <button class="ctrl-btn" id="btn-play" onclick="togglePlay()">▶️ 自動漫遊</button>
          <button class="ctrl-btn secondary" onclick="stepPrev()">⏮️</button>
          <button class="ctrl-btn secondary" onclick="stepNext()">⏭️</button>
          <button class="ctrl-btn voice-on" id="btn-voice" onclick="toggleVoice()">🔊 語音導遊：開</button>
          <button class="ctrl-btn secondary" onclick="speakCurrentStop()">🎙️ 重聽本站</button>
          <button class="ctrl-btn secondary" onclick="toggleCameraFollow()" id="btn-cam">🎥 跟隨</button>
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
        let followCam = true;
        let voiceEnabled = true;
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
              <rect x="10" y="26" width="12" height="22" rx="5" fill="#ea580c" stroke="#fff" stroke-width="2"/>
              <rect x="18" y="24" width="26" height="26" rx="9" fill="#2563eb" stroke="#fff" stroke-width="2.5"/>
              <circle cx="32" cy="14" r="11" fill="#fde68a" stroke="#fff" stroke-width="2.5"/>
              <rect x="26" y="10" width="16" height="6" rx="3" fill="#0f172a"/>
              <rect x="21" y="48" width="8" height="14" rx="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>
              <rect x="33" y="48" width="8" height="14" rx="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>
            </svg>
          </div>
          <div class="avatar-shadow"></div>
        `;

        const travelerMarker = new maplibregl.Marker({{ element: travelerEl, anchor: 'bottom' }})
          .setLngLat([places[0].lon, places[0].lat])
          .addTo(map);

        // AI 語音播報函式 (Web Speech API)
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
            btn.innerText = '🔊 語音導遊：開';
            btn.classList.add('voice-on');
            btn.classList.remove('secondary');
            speakCurrentStop();
          }} else {{
            window.speechSynthesis.cancel();
            btn.innerText = '🔇 語音導遊：關';
            btn.classList.remove('voice-on');
            btn.classList.add('secondary');
          }}
        }}

        map.on('load', () => {{
          const routeCoords = places.map(p => [p.lon, p.lat]);

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

          places.forEach((p, idx) => {{
            const pin = document.createElement('div');
            pin.className = 'stop-pin' + (idx === 0 ? ' active' : '') + (p.is_checked ? ' stamped' : '');
            const stampPrefix = p.is_checked ? '💮 ' : '';
            pin.innerHTML = `${{stampPrefix}}${{idx + 1}}. ${{p.name}}`;
            pin.onclick = () => {{
              jumpToStop(idx);
              speakStopGuide(idx, null);
            }};

            new maplibregl.Marker({{ element: pin, anchor: 'bottom' }})
              .setLngLat([p.lon, p.lat])
              .setPopup(new maplibregl.Popup({{ offset: 25 }}).setHTML(
                `<b>第 ${{idx + 1}} 站：${{p.name}} ${{p.is_checked ? '💮已打卡' : ''}}</b><br/>` +
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
            const smoothT = t * t * (3 - 2 * t);
            const curLon = start.lon + (end.lon - start.lon) * smoothT;
            const curLat = start.lat + (end.lat - start.lat) * smoothT;

            travelerMarker.setLngLat([curLon, curLat]);

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
              // 抵達新站點時，播報 AI 隨身語音導遊，播畢後繼續下一段
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
            travelerMarker.setLngLat([places[0].lon, places[0].lat]);
            updateHudAtStop(0);
          }}
          walkSegment(currentIndex, currentIndex + 1, () => {{
            if (currentIndex < places.length - 1) {{
              playLoop();
            }} else {{
              isPlaying = false;
              document.getElementById('btn-play').innerText = '🔄 重新漫遊';
              document.getElementById('bubble-text').innerText = '🏁 全程巡禮完成！別忘了去集章卡打卡喔！';
            }}
          }});
        }}

        function togglePlay() {{
          isPlaying = !isPlaying;
          const btn = document.getElementById('btn-play');
          if (isPlaying) {{
            btn.innerText = '⏸️ 暫停漫遊';
            // 若在起點剛開始，先播報第 1 站導覽再出發
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
          speakStopGuide(target, null);
        }}

        function stepNext() {{
          const target = Math.min(places.length - 1, currentIndex + 1);
          jumpToStop(target);
          speakStopGuide(target, null);
        }}

        function toggleCameraFollow() {{
          followCam = !followCam;
          document.getElementById('btn-cam').innerText = followCam ? '🎥 跟隨' : '🎥 自由';
        }}

        function changeSpeed() {{
          speedMultiplier = parseFloat(document.getElementById('speed-sel').value || '2');
        }}
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
      st.session_state["checked_places"] = set()
      st.session_state["checkin_photos"] = {}
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

  # 計算目前集章進度
  checked_set = st.session_state.get("checked_places", set())
  total_stops = len(enriched_places)
  stamped_count = sum(
      1 for p in enriched_places if p.get("name") in checked_set
  )

  # 頂部總覽儀表板 (5 張 KPI 卡片，新增集章進度)
  boba_count = round(summary["calories"] / 450, 1)
  k1, k2, k3, k4, k5 = st.columns(5)
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
  with k5:
    st.markdown(
        f'<div class="stat-card"><div class="stat-val">💮 {stamped_count} / {total_stops} 枚</div>'
        '<div class="stat-label">打卡集章解鎖進度</div></div>',
        unsafe_allow_html=True,
    )

  st.write("")

  # 頂部動作列：Google Maps 導航 + 行事曆匯出 + 一鍵全集章展示
  act_col1, act_col2, act_col3, act_col4 = st.columns([1.8, 1.1, 1.1, 1.1])
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
    if st.button("💮 一鍵全蓋章 (Demo 展示)", use_container_width=True):
      st.session_state["checked_places"] = {
          p.get("name") for p in enriched_places
      }
      st.balloons()
      st.rerun()
  with act_col4:
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

  col1, col2 = st.columns([1.08, 1.32])

  # 左欄：智慧時間軸清單（含 AI 隨身語音導遊 & 單站打卡蓋章）
  with col1:
    st.subheader(f"📋 順路時間軸 & 隨身語音導覽（共 {total_stops} 站）")
    cat_icons = {"美食": "🍜", "景點": "📸", "購物": "🛍️", "住宿": "🏨"}

    for i, p in enumerate(enriched_places, 1):
      p_name = p.get("name", f"第{i}站")
      is_done = p_name in checked_set

      if i > 1:
        st.caption(
            f"⬇️ *移動約 {p['dist_from_prev_km']} km（預計 {p['move_mins_from_prev']} 分鐘）*"
        )
      with st.container(border=True):
        c_title, c_stamp_btn, c_del = st.columns([4.2, 1.6, 0.7])
        cat_icon = cat_icons.get(p.get("category", "景點"), "📍")
        stamp_badge = " 💮`已蓋章`" if is_done else ""
        c_title.markdown(
            f"#### `{p['arrive_time']} - {p['depart_time']}` 第 {i} 站：{p_name}{stamp_badge}"
        )

        # 單站打卡蓋章切換按鈕
        btn_label = "✅ 已打卡" if is_done else "💮 打卡蓋章"
        if c_stamp_btn.button(
            btn_label,
            key=f"stamp_btn_{i}_{p_name}",
            type="primary" if not is_done else "secondary",
            use_container_width=True,
        ):
          if is_done:
            st.session_state["checked_places"].discard(p_name)
          else:
            st.session_state["checked_places"].add(p_name)
            if len(st.session_state["checked_places"]) == total_stops:
              st.balloons()
          st.rerun()

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

        # 展開上傳該站打卡認證照（選填，會自動合成進紀念海報）
        with st.expander("📷 上傳本站踩點認證照 / 查看街景"):
          photo_file = st.file_uploader(
              f"上傳『{p_name}』踩點合照（將自動貼入集章紀念海報）",
              type=["jpg", "jpeg", "png"],
              key=f"photo_up_{i}_{p_name}",
          )
          if photo_file is not None:
            st.session_state["checkin_photos"][p_name] = photo_file.getvalue()
            st.session_state["checked_places"].add(p_name)
            st.success("✅ 已儲存踩點照片並自動完成蓋章！")

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

  # 右欄：3D 旅人語音漫遊、打卡進度集章卡、2D Folium 切換
  with col2:
    tab_3d, tab_stamp, tab_2d = st.tabs([
        "🕹️ 3D 旅人漫遊 + AI 語音導遊",
        f"💮 打卡進度集章卡 ({stamped_count}/{total_stops})",
        "🗺️ 2D 經典路線圖 (Folium)",
    ])

    with tab_3d:
      render_3d_walking_map(
          enriched_places, checked_set=checked_set, travel_mode=travel_mode
      )

    with tab_stamp:
      st.subheader("💮 旅遊踩點集章卡 (Stamp Rally)")
      progress_ratio = stamped_count / total_stops if total_stops else 0.0
      if progress_ratio == 0:
        rank_title = "🌱 剛出發的初心旅人"
      elif progress_ratio < 1.0:
        rank_title = "🔥 順路探索冒險家"
      else:
        rank_title = "👑 全程完美制霸王！"

      st.progress(
          progress_ratio,
          text=f"目前稱號：【{rank_title}】｜已收集 {stamped_count} / {total_stops} 枚紀念印章（{int(progress_ratio * 100)}%）",
      )

      # 渲染日本車站紀念章風格網格
      stamp_cards_html = ['<div class="stamp-grid">']
      for idx, p in enumerate(enriched_places, 1):
        p_name = p.get("name", f"第{idx}站")
        done = p_name in checked_set
        slot_cls = "stamp-slot done" if done else "stamp-slot"
        seal_cls = "stamp-seal unlocked" if done else "stamp-seal locked"
        seal_inner = (
            f"<div>第 {idx} 站</div><div style='font-size:15px;'>💮制霸</div><div>{p['arrive_time']}</div>"
            if done
            else f"<div>第 {idx} 站</div><div>待踩點</div>"
        )
        stamp_cards_html.append(
            f'<div class="{slot_cls}">'
            f'  <div class="{seal_cls}">{seal_inner}</div>'
            f'  <div style="font-weight:700; font-size:13px; color:#0f172a;">{p_name}</div>'
            f'  <div style="font-size:11.5px; color:#64748b; margin-top:2px;">{p.get("category", "景點")}</div>'
            f"</div>"
        )
      stamp_cards_html.append("</div>")
      st.markdown("".join(stamp_cards_html), unsafe_allow_html=True)

      c_act1, c_act2 = st.columns(2)
      with c_act1:
        if st.button(
            "🎉 一鍵蓋滿全部印章 (Demo 預覽)",
            key="tab_stamp_all",
            use_container_width=True,
        ):
          st.session_state["checked_places"] = {
              p.get("name") for p in enriched_places
          }
          st.balloons()
          st.rerun()
      with c_act2:
        if st.button(
            "🔄 重置所有印章", key="tab_stamp_reset", use_container_width=True
        ):
          st.session_state["checked_places"] = set()
          st.session_state["checkin_photos"] = {}
          st.rerun()

      st.markdown("---")
      st.markdown("#### 🖼️ 即時合成「今日制霸集章紀念海報」")
      st.caption(
          "系統已根據您的順路行程、集章狀態與上傳的踩點照片，動態繪製專屬紀念海報："
      )

      poster_bytes = generate_stamp_poster_png(
          enriched_places,
          summary,
          checked_set,
          st.session_state.get("checkin_photos", {}),
      )
      st.download_button(
          "📥 下載高畫質「今日制霸集章海報」(.png)",
          data=poster_bytes,
          file_name="stamp_rally_poster.png",
          mime="image/png",
          type="primary",
          use_container_width=True,
      )
      st.image(poster_bytes, use_container_width=True)

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
          is_done = p.get("name") in checked_set
          if lat and lon:
            popup_content = (
                f"<b>第 {i} 站 ({p['arrive_time']})：{p.get('name')}</b><br>"
                f"{p.get('must_try_or_see')}"
            )
            folium.Marker(
                location=[lat, lon],
                tooltip=f"第 {i} 站：{p.get('name')} {'(💮已打卡)' if is_done else ''}",
                popup=folium.Popup(popup_content, max_width=250),
                icon=folium.Icon(
                    color="green" if is_done else ("red" if i == 1 else "blue"),
                    icon="check" if is_done else ("flag" if i == 1 else "bookmark"),
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
      "免輸入 API Key、免上傳圖片即可體驗 **3D 旅人漫遊、AI 隨身語音導遊與打卡集章海報**！"
  )