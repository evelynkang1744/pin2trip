import json
import urllib.parse
import folium
from geopy.distance import geodesic
from google import genai
from google.genai import types
from PIL import Image
import streamlit as st
from streamlit_folium import st_folium

# ----------------- 頁面基本設定 -----------------
st.set_page_config(page_title="截圖轉行程 Travel Pin-to-Itinerary", layout="wide")
st.title("✈️ 社畜截圖轉行程 AI 助手")
st.caption("自動萃取社群截圖中的景點、最佳順路動線排序與一鍵導航！")

# ----------------- 初始化 Client -----------------
API_KEY = "AQ.Ab8RN6KtLQoIhclSx2mhicROJ-iwHekciJE54dyUXGdwRwc1mg"
client = genai.Client(api_key=API_KEY)

# ----------------- 輔助函式：路徑智慧排序 (TSP 貪婪演算法) -----------------
def optimize_route(places_list):
  """依據地理距離排序，以第一個景點為起點，每次挑選距離最近的下一個點。"""
  valid_places = [
      p for p in places_list if p.get("lat") is not None and p.get("lon") is not None
  ]
  no_coords = [
      p for p in places_list if p.get("lat") is None or p.get("lon") is None
  ]

  if len(valid_places) <= 2:
    return valid_places + no_coords

  unvisited = valid_places[1:]
  current = valid_places[0]
  optimized = [current]

  while unvisited:
    current_coord = (current["lat"], current["lon"])
    # 找出與目前點距離最短的下一個景點
    next_place = min(
        unvisited,
        key=lambda p: geodesic(current_coord, (p["lat"], p["lon"])).kilometers,
    )
    optimized.append(next_place)
    unvisited.remove(next_place)
    current = next_place

  return optimized + no_coords


# ----------------- 輔助函式：生成 Google Maps 多點導航連結 -----------------
def generate_google_maps_directions_url(places_list):
  """生成一次串聯所有景點的 Google Maps 導航 URL。"""
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

  # 中途途經點 (waypoints)
  if len(valid_places) > 2:
    waypoint_names = [
        f"{p['name']} {p.get('city', '')}" for p in valid_places[1:-1]
    ]
    waypoints = urllib.parse.quote("|".join(waypoint_names))
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode=walking"
  else:
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=walking"

  return url


# ----------------- 側邊欄：上傳與設定 -----------------
st.sidebar.header("📸 上傳旅遊截圖")
uploaded_files = st.sidebar.file_uploader(
    "支援多張 JPG / PNG 截圖上傳",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

start_button = st.sidebar.button(
    "🚀 開始辨識並規劃行程", type="primary", use_container_width=True
)


# ----------------- 核心解析函式 -----------------
def analyze_image(image_bytes):
  image = Image.open(image_bytes)
  prompt = """
    你是一個專業的旅遊行程規劃助手。請分析使用者上傳的這張旅遊/美食/景點截圖，並提取出核心的地點資訊。
    若一張圖包含多個推薦地點請全部列出。
    請務必嚴格輸出為 JSON 陣列格式，格式範例：
    [
      {
        "name": "地點名稱（最精確的中/原文店名或景點名）",
        "city": "所在城市/地區（例如：日本京都、芬蘭羅瓦涅米）",
        "category": "美食 / 景點 / 購物 / 住宿",
        "must_try_or_see": "推薦招牌菜或拍照亮點（15字以內）",
        "lat": 粗估緯度(float),
        "lon": 粗估經度(float)
      }
    ]
    """

  models_to_try = [
      "gemini-flash-lite-latest",
      "gemini-3.5-flash-lite",
      "gemini-flash-latest",
      "gemini-3.8-flash",
  ]

  for model_name in models_to_try:
    try:
      response = client.models.generate_content(
          model=model_name,
          contents=[image, prompt],
          config=types.GenerateContentConfig(
              response_mime_type="application/json",
              temperature=0.2,
          ),
      )
      return json.loads(response.text)
    except Exception:
      continue
  return []


# ----------------- 點擊按鈕執行分析 -----------------
if start_button:
  if not uploaded_files:
    st.sidebar.warning("請先上傳至少一張截圖！")
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

    status_text.text("✅ 分析完成！")
    st.session_state["places"] = all_places

# ----------------- 畫面展示區 -----------------
if "places" in st.session_state and st.session_state["places"]:
  places = st.session_state["places"]

  # 提供「順路動線優化」切換選項
  st.sidebar.markdown("---")
  st.sidebar.subheader("⚙️ 行程偏好設定")
  is_optimized = st.sidebar.checkbox(
      "啟用智慧順路排序 (避免折返跑)", value=True
  )

  if is_optimized:
    places = optimize_route(places)

  # 頂部動作列：多點導航匯出按鈕
  directions_url = generate_google_maps_directions_url(places)
  if directions_url:
    st.success(
        "💡 系統已自動依地理距離為您安排最佳順序，點擊下方按鈕即可開啟完整路線導航："
    )
    st.link_button(
        "🗺️ 開啟 Google Maps 一日遊多點導航路線",
        directions_url,
        type="primary",
    )

  col1, col2 = st.columns([1, 1])

  # 左欄：景點清單列表
  with col1:
    st.subheader(f"📍 推薦拜訪清單（共 {len(places)} 處）")
    for i, p in enumerate(places, 1):
      with st.container(border=True):
        st.markdown(f"### 第 {i} 站：{p.get('name', '未知地點')}")
        st.write(
            f"🏷️ **類別**：{p.get('category', '景點')} ｜ 🏙️"
            f" **城市**：{p.get('city', '')}"
        )
        st.write(f"💡 **推薦看點/必吃**：{p.get('must_try_or_see', '無')}")

        # 單點精確定位搜尋連結
        search_text = f"{p.get('name', '')} {p.get('city', '')}".strip()
        single_map_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(search_text)}"
        st.markdown(f"[🔍 單獨查看此地點資訊]({single_map_url})")

  # 右欄：Folium 互動地圖
  with col2:
    st.subheader("🗺️ 最佳順序動線地圖")

    valid_coords = [
        (p.get("lat"), p.get("lon"))
        for p in places
        if p.get("lat") and p.get("lon")
    ]

    if valid_coords:
      start_lat, start_lon = valid_coords[0]
      m = folium.Map(location=[start_lat, start_lon], zoom_start=13)

      for i, p in enumerate(places, 1):
        lat, lon = p.get("lat"), p.get("lon")
        if lat and lon:
          popup_content = (
              f"<b>第 {i} 站：{p.get('name')}</b><br>{p.get('must_try_or_see')}"
          )
          # 使用藍底帶數字的標記
          folium.Marker(
              location=[lat, lon],
              tooltip=f"第 {i} 站：{p.get('name')}",
              popup=folium.Popup(popup_content, max_width=250),
              icon=folium.Icon(color="blue", icon="bookmark", prefix="fa"),
          ).add_to(m)

      if len(valid_coords) > 1:
        folium.PolyLine(
            locations=valid_coords,
            color="#2563EB",
            weight=4,
            opacity=0.8,
            dash_array="6, 8",
        ).add_to(m)

      st_folium(m, width="100%", height=550)
    else:
      st.warning("未能取得有效經緯度座標。")

elif not uploaded_files:
  st.info(
      "👈 請在左側面板上傳 1~3 張旅遊截圖，並點擊「開始辨識並規劃行程」。"
  )