"""即時監控頁：WebSocket 即時資料折線圖/柱狀圖，異常紅色標記。"""
import pandas as pd
import plotly.express as px
import streamlit as st

from state import get_token, require_login
from ws_client import fetch_realtime_batch

require_login()

st.set_page_config(page_title="即時監控", page_icon="📊", layout="wide")
st.title("📊 即時監控")

st.caption("每次重新整理會從 WebSocket 讀取最新即時資料；可開啟自動更新。")

if "rt_buffer" not in st.session_state:
    st.session_state["rt_buffer"] = []

col1, col2 = st.columns([1, 3])
with col1:
    auto = st.toggle("自動更新（每 2 秒）", value=False)
    if st.button("立即更新"):
        st.rerun()

batch = fetch_realtime_batch(get_token(), max_messages=5)
if batch:
    st.session_state["rt_buffer"].extend(batch)
    st.session_state["rt_buffer"] = st.session_state["rt_buffer"][-100:]

buffer = st.session_state["rt_buffer"]

if not buffer:
    st.info("尚未收到即時資料（請稍候或確認後端生成器運作中）。")
else:
    df = pd.DataFrame(buffer)
    df["generated_at"] = pd.to_datetime(df["generated_at"])

    anomaly_count = int(df["is_anomaly"].sum())
    st.metric("最近異常筆數", anomaly_count)

    fig_line = px.line(
        df, x="generated_at", y="value", color="category",
        title="即時數值趨勢（折線圖）", markers=True,
    )
    # 異常點以紅色標記
    anomalies = df[df["is_anomaly"]]
    if not anomalies.empty:
        fig_line.add_scatter(
            x=anomalies["generated_at"], y=anomalies["value"],
            mode="markers", marker=dict(color="red", size=12, symbol="x"),
            name="異常",
        )
    st.plotly_chart(fig_line, use_container_width=True)

    latest_by_cat = df.groupby("category")["value"].last().reset_index()
    fig_bar = px.bar(
        latest_by_cat, x="category", y="value",
        title="各分類最新數值（柱狀圖）", color="category",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(df.tail(20).iloc[::-1], use_container_width=True)

if auto:
    import time
    time.sleep(2)
    st.rerun()
