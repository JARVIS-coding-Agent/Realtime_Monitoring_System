"""資料分析頁：統計、分類聚合、趨勢圖、Excel 匯出。"""
import pandas as pd
import plotly.express as px
import streamlit as st

import api_client
from state import require_login

require_login()

st.set_page_config(page_title="資料分析", page_icon="📈", layout="wide")
st.title("📈 資料分析")

c1, c2 = st.columns(2)
with c1:
    category = st.text_input("分類（可留空）", "")
with c2:
    interval = st.selectbox("趨勢分桶", ["day", "hour"])

params = {}
if category:
    params["category"] = category

# === 統計 ===
st.subheader("統計指標")
try:
    stats = api_client.get_json("/api/analytics/stats", params=params)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("筆數", stats["count"])
    m2.metric("總計", round(stats["sum"], 2))
    m3.metric("平均", round(stats["avg"], 2))
    m4.metric("最小", round(stats["min"], 2))
    m5.metric("最大", round(stats["max"], 2))
except api_client.ApiError as exc:
    st.error(exc.detail)

# === 分類聚合 ===
st.subheader("分類聚合")
try:
    agg = api_client.get_json("/api/analytics/aggregate")
    if agg:
        df_agg = pd.DataFrame(agg)
        st.plotly_chart(
            px.bar(df_agg, x="category", y="sum", color="category", title="各分類總計"),
            use_container_width=True,
        )
        st.dataframe(df_agg, use_container_width=True)
    else:
        st.info("沒有資料。")
except api_client.ApiError as exc:
    st.error(exc.detail)

# === 趨勢 ===
st.subheader("趨勢")
try:
    trend = api_client.get_json("/api/analytics/trend", params={"interval": interval})
    if trend:
        df_trend = pd.DataFrame(trend)
        df_trend["bucket"] = pd.to_datetime(df_trend["bucket"])
        st.plotly_chart(
            px.line(df_trend, x="bucket", y="avg", title="平均值趨勢", markers=True),
            use_container_width=True,
        )
    else:
        st.info("此範圍沒有資料。")
except api_client.ApiError as exc:
    st.error(exc.detail)

# === Excel 匯出 ===
st.subheader("匯出")
if st.button("下載 Excel"):
    try:
        content = api_client.get_bytes("/api/analytics/export", params=params)
        st.download_button(
            "點此下載 analytics_export.xlsx",
            data=content,
            file_name="analytics_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except api_client.ApiError as exc:
        st.error(exc.detail)
