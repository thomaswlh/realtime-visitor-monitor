# 電子廣告板人流偵測與視覺化儀表板

本專案包含以下三個主要部分，協助快速分析電子廣告板或展覽入口的人流情況及停留行為：

* `people_counter.py`: 即時人流偵測與進出計數。
* `region_tweak_gui.py` / `region_tweak_web.py`: 用於快速調整並預覽計數區域的 GUI 或網頁介面。
* `dashboard.py`: 數據視覺化儀表板（Streamlit）。

---

## 功能特色

* 📹 **人流自動偵測與進出計數（使用OpenCV、Norfair追蹤及MobileNet-SSD模型）**
* 🎯 **可自訂計數區域與鏡頭角度校正**
* 📝 **自動將進出人數、停留時間記錄到CSV日誌**
* 📊 **即時儀表板展示數據分析（Streamlit）**
* 🚦 **一鍵啟動，自動化記錄與分析**

---

## 專案目錄

* [安裝 Installation](#安裝-installation)
* [人流偵測程式說明（people\_counter.py）](#人流偵測程式說明-people_counterpy)
* [區域調整與預覽工具說明（region\_tweak\_gui.py / region\_tweak\_web.py）](#區域調整與預覽工具說明-region_tweak)
* [視覺化儀表板說明（dashboard.py）](#視覺化儀表板說明-dashboardpy)
* [常見問題 FAQ](#常見問題-faq)
* [License 授權](#license-授權)

---

## 安裝 Installation

1. Clone 本專案：

   ```bash
   git clone https://github.com/thomaswlh/realtime-visitor-monitor.git
   cd realtime-visitor-monitor
   ```

2. 安裝相關依賴（建議使用虛擬環境）：

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows 使用 venv\Scripts\activate
   pip install -r requirements.txt
   ```

主要依賴包括：

* `opencv-python`
* `norfair`
* `nicegui` (若使用region\_tweak\_web.py)
* `kivy` (若使用region\_tweak\_gui.py)
* `streamlit`
* `pandas`

---

## 人流偵測程式說明 (`people_counter.py`)

### 使用方法

配置`config.json`:

```json
{
  "url": "0"
}
```

啟動偵測程式：

```bash
python people_counter.py -p models/MobileNetSSD_deploy.prototxt \
    -m models/MobileNetSSD_deploy.caffemodel
```

啟動偵測程式 (使用測試影片)：

```bash
python people_counter.py --prototxt detector/MobileNetSSD_deploy.prototxt --model detector/MobileNetSSD_deploy.caffemodel --input utils/data/tests/test_1.mp4
```

參數範例（設定區域）：

```bash
--rect-x 100 --rect-y 150 --rect-w 400 --rect-h 200 --tilt-angle 10
```

偵測資料儲存在：`utils/data/logs/counting_data.csv`

---

## 區域調整與預覽工具說明 (`region_tweak_gui.py` / `region_tweak_web.py`)

本工具提供即時視覺介面，用於調整及預覽人流計數區域的座標、尺寸與傾斜角度。

### 使用GUI版本（Kivy）

```bash
python region_tweak_gui.py
```

### 使用Web版本（NiceGUI）

```bash
python region_tweak_web.py
```

透過互動介面，即時調整並獲取最佳參數設定。

---

## 視覺化儀表板說明 (`dashboard.py`)

啟動Streamlit儀表板查看分析結果：

```bash
streamlit run dashboard.py
```

儀表板功能包含：

* 總人數、平均停留時間、中位停留時間及有效停留比例
* 可依據不同時間區間（1分鐘, 15分鐘、30分鐘、小時、天）進行分析
* 每10秒刷新數據來源

---

## 常見問題 FAQ

**Q1：計數區域該如何調整？**

使用`region_tweak_gui.py`或`region_tweak_web.py`進行直覺化調整。

**Q2：如何更換模型？**

將MobileNet-SSD模型替換為其他兼容的物件偵測模型即可。

**Q3：如何處理不同的攝影機URL？**

修改`config.json`的`url`值，例如`0`（本地攝影機）或其他RTSP網址。

---

## License 授權

MIT License

---

> Powered by Python, OpenCV, Norfair, NiceGUI, Kivy, and Streamlit
