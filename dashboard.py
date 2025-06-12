import streamlit as st
import pandas as pd
import numpy as np

# ---- 載入並清理資料 ----
@st.cache_data(ttl=10) 
def load_data(filename):
    df = pd.read_csv(filename)
    df["In Time"] = pd.to_datetime(df["In Time"], errors="coerce")
    df["Out Time"] = pd.to_datetime(df["Out Time"], errors="coerce")
    df["Stay Duration"] = pd.to_numeric(df["Stay Duration"], errors="coerce")
    valid = df["Stay Duration"].notna() & (df["Stay Duration"] >= 0)
    return df[valid].reset_index(drop=True)

st.title("廣告機人流統計數據")

# ---- 側邊欄控制 ----
st.sidebar.header("設定")
csv_file = st.sidebar.text_input("CSV 檔案路徑", value="utils/data/logs/counting_data.csv")
interval = st.sidebar.selectbox("時間顯示單位", ["1分鐘","15分鐘", "30分鐘", "1小時", "1天"])
engaged_sec = st.sidebar.slider("有效停留最少秒數", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

interval_map = {
    "1分鐘": "1T",
    "15分鐘": "15T",
    "30分鐘": "30T",
    "小時": "H",
    "天": "D"
}
freq = interval_map[interval]

df = load_data(csv_file)

# ---- 計算主要指標 ----
st.subheader("指標")

total_visitors = len(df)
avg_stay = df["Stay Duration"].mean()
median_stay = df["Stay Duration"].median()
engaged = df[df["Stay Duration"] >= engaged_sec]
percent_engaged = (len(engaged) / total_visitors * 100) if total_visitors else 0

col1, col2, col3, col4 = st.columns([1.5, 2, 2, 2.5]) 
col1.metric("👣 人流總數", total_visitors)
col2.metric("⏱ 平均停留時間（秒）", f"{avg_stay:.2f}" if not np.isnan(avg_stay) else "-")
col3.metric("🧍 停留時間中位數（秒）", f"{median_stay:.2f}" if not np.isnan(median_stay) else "-")
col4.metric(f"👍 有效停留比率（≥{engaged_sec}秒）", f"{percent_engaged:.1f}%")

# ---- 區間分組資料 ----
df_time = df.set_index("In Time")
footfall = df_time["Move In"].resample(freq).count()
avg_stays = df_time["Stay Duration"].resample(freq).mean()

# ---- 圖表 ----

st.subheader(f"人流量（以{interval}為單位）")
st.bar_chart(footfall, use_container_width=True)

st.subheader(f"平均停留時間（以{interval}為單位）")
st.line_chart(avg_stays, use_container_width=True)

# ---- 原始資料預覽 ----
with st.expander("顯示原始資料"):
    st.dataframe(df)

# ---- 異常提示 ----
if (df["Stay Duration"] < 0).any():
    st.warning("⚠️ 檢測到負值停留時間（已排除）")
if df.isnull().any().any():
    st.warning("⚠️ 檢測到缺失或無效資料（已排除）")

st.caption("由 Streamlit 提供支援。可在側邊欄調整檔案路徑及統計區間。")
