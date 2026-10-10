import base64
import json
import os
import urllib.parse
from PIL import Image
import folium
from geopy.distance import geodesic
import requests
import streamlit as st
from streamlit_folium import st_folium

# ----------------- 頁面基本設定 -----------------
st.set_page_config(
    page_title="截圖轉行程 Travel Pin-to-Itinerary", layout="wide"
)
st.title("✈️ 上班截圖、下班出發：社畜無腦排行程 AI")
st.caption("IG、小紅書截圖一鍵丟！自動抓出神秘景點，排好順路動線直接導航出發！！")
st.caption("只要會截圖，剩下的交給 AI！")

# ----------------- 側邊欄：API 金鑰設定 -----------------
st.sidebar.header("🔑 使用者設定")
st.sidebar.markdown(
    "本工具使用您個人的 Google Gemini 額度。\n"
    "[👉 點此免費取得 Gemini API Key](https://aistudio.google.com/app/apikey)"
)

# 從 Secrets 或環境變數讀取預設值（若有的話）
raw_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
clean_default = (
    str(raw_key).strip().strip('"').strip("'") if raw_key else ""
)

user_key = st.sidebar.text_input(
    "請輸入您的 Gemini API Key",
    value=clean_default,
    type="password",
    placeholder="AIzaSy...",
    help="金鑰僅供本次瀏覽階段使用，不會儲存於伺服器。",
)

# 備援模型清單（優先使用輕量、排隊較少的模型繞開 503 尖峰）
MODELS_TO_TRY = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

# 側邊欄：快速連線測試按鈕
if st.sidebar.button("🔍 測試 Key 連線狀態"):
  if not user_key:
    st.sidebar.error("請先輸入 API Key！")
  else:
    key = user_key.strip().strip('"').strip("'")
    success = False
    last_msg = ""

    for model_name in MODELS_TO_TRY:
      test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
      payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
      try:
        res = requests.post(test_url, json=payload, timeout=10)
        if res.status_code == 200:
          st.sidebar.success(f"✅ 連線成功！當前可用模型：{model_name}")
          success = True
          break
        else:
          last_msg = f"{model_name} ({res.status_code}): {res.text}"
      except Exception as e:
        last_msg = f"{model_name}: {e}"

    if not success:
      st.sidebar.error(f"❌ 全部模型連線失敗，最後錯誤：{last_msg}")

if not user_key:
  st.info("👈 請在左側輸入您的 Gemini API Key 即可開始使用。")
  st.stop()

clean_api_key = user_key.strip().strip('"').strip("'")


# ----------------- 輔助函式：路徑智慧排序 (TSP 貪婪演算法) -----------------
def optimize_route(places_list):
  """依據地理距離排序，以第一個景點為起點，每次挑選距離最近的下一個點。"""
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

  unvisited = valid_places[1:]
  current = valid_places[0]
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


# ----------------- 輔助函式：生成 Google Maps 多點導航連結 -----------------
def generate_google_maps_directions_url(places_list):
  """生成串聯所有景點的 Google Maps 導航 URL。"""
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
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode=walking"
  else:
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=walking"

  return url


# ----------------- 側邊欄：上傳與觸發按鈕 -----------------
st.sidebar.markdown("---")
st.sidebar.header("📸 上傳旅遊截圖")
uploaded_files = st.sidebar.file_uploader(
    "支援多張 JPG / PNG 截圖上傳",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)
start_button = st.sidebar.button(
    "🚀 開始辨識並規劃行程", type="primary", use_container_width=True
)


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
        "city": "所在城市/地區（例如：日本京都、芬蘭羅瓦涅米）",
        "category": "美食 / 景點 / 購物 / 住宿",
        "must_try_or_see": "推薦招牌菜或拍照亮點（15字以內）",
        "lat": 粗估緯度(float),
        "lon": 粗估經度(float)
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

  # 遍歷模型清單，遇到 503 或錯誤自動切換下一款
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
        continue
    except Exception as e:
      errors.append(f"{model_name} ({e})")
      continue

  st.error("所有備援模型皆呼叫失敗：\n" + "\n".join(errors))
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

    if all_places:
      status_text.text("✅ 分析完成！")
      st.session_state["places"] = all_places
    else:
      status_text.text("⚠️ 未能萃取出景點，請檢查錯誤日誌。")

# ----------------- 畫面展示區 -----------------
if "places" in st.session_state and st.session_state["places"]:
  places = st.session_state["places"]

  # 提供順路動線優化開關
  st.sidebar.markdown("---")
  st.sidebar.subheader("⚙️ 行程偏好設定")
  is_optimized = st.sidebar.checkbox(
      "啟用智慧順路排序 (避免折返跑)", value=True
  )

  if is_optimized:
    places = optimize_route(places)

  # 頂部動作列：一鍵 Google Maps 導航
  directions_url = generate_google_maps_directions_url(places)
  if directions_url:
    st.success("💡 系統已自動依地理距離為您安排最佳順序，點擊下方按鈕開啟完整多點導航：")
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

        # 使用店名 + 城市組成的精確搜尋連結
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