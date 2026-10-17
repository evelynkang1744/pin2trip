import json
import os
import time
from PIL import Image
from google import genai
from google.genai import types

# 改為以下安全寫法：
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))

if not api_key:
  st.error("請在 Streamlit Secrets 設定中填入 GEMINI_API_KEY！")
  st.stop()

client = genai.Client(api_key=api_key)

# 3. 載入本地截圖
image_path = "/Users/tingcih/Desktop/Programming/Image_search/IMG_7296.jpg"

if not os.path.exists(image_path):
    print(f"錯誤：找不到圖片檔案 {image_path}，請先放入一張截圖！")
    exit(1)

image = Image.open(image_path)

# 4. 設計結構化 Prompt
prompt = """
你是一個專業的旅遊行程規劃助手。請分析使用者上傳的這張旅遊/美食/景點截圖，並提取出核心的地點資訊。

請務必嚴格輸出為 JSON 陣列格式，若一張圖包含多個推薦地點請全部列出，單一地點也請放在陣列中。
格式範例：
[
  {
    "name": "地點名稱（請給出最精確的中/原文店名或景點名）",
    "city": "所在城市/地區（例如：日本京都、台灣台北）",
    "category": "美食 / 景點 / 購物 / 住宿",
    "must_try_or_see": "截圖中特別推薦的招牌菜、拍照亮點或特色（15字以內）",
    "lat": 粗估緯度(float，例如 35.0116),
    "lon": 粗估經度(float，例如 135.7681)
  }
]
"""


# 5. 呼叫穩定的 gemini-2.5-flash
models_to_try = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

response = None

for model_name in models_to_try:
    print(f"正在嘗試模型：{model_name} ...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        print(f"✅ 成功連線！由 {model_name} 產出結果。")
        break  # 成功取得就跳出
    except Exception as e:
        print(f"⚠️ {model_name} 回應失敗（原因：{e}）")
        print("切換至下一個備援模型...")
        time.sleep(1)

# 5. 印出解析結果
if response:
    try:
        places_data = json.loads(response.text)
        print("\n✅ 解析成功！取得結構化資料如下：\n")
        print(json.dumps(places_data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("\n❌ 原始回應非標準 JSON：")
        print(response.text)
else:
    print("\n❌ 所有備選模型均無法回應，請稍候再試。")