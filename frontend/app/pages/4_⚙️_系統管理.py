"""系統管理頁（僅 Admin）：使用者列表/角色管理、系統日誌、DB 狀態、即時歷史。"""
import pandas as pd
import streamlit as st

import api_client
from state import get_role, require_login

require_login()

st.set_page_config(page_title="系統管理", page_icon="⚙️", layout="wide")
st.title("⚙️ 系統管理")

if get_role() != "admin":
    st.error("此頁僅限管理員存取。")
    st.stop()

tab_users, tab_logs, tab_db, tab_history = st.tabs(["使用者", "系統日誌", "資料庫狀態", "即時歷史"])

with tab_users:
    st.subheader("使用者列表")
    try:
        users = api_client.get_json("/api/admin/users")
        st.dataframe(pd.DataFrame(users), use_container_width=True)
    except api_client.ApiError as exc:
        st.error(exc.detail)

    st.subheader("變更角色")
    with st.form("role_form"):
        uid = st.number_input("使用者 ID", min_value=1, step=1)
        new_role = st.selectbox("新角色", ["admin", "user", "viewer"])
        submitted = st.form_submit_button("變更")
    if submitted:
        try:
            api_client.put_json(f"/api/admin/users/{int(uid)}/role", {"role": new_role})
            st.success("角色已更新")
            st.rerun()
        except api_client.ApiError as exc:
            st.error(exc.detail)

with tab_logs:
    st.subheader("系統日誌")
    level = st.selectbox("等級篩選", ["", "INFO", "WARNING", "ERROR"])
    params = {"page": 1, "page_size": 100}
    if level:
        params["level"] = level
    try:
        logs = api_client.get_json("/api/admin/logs", params=params)
        st.caption(f"共 {logs['total']} 筆")
        if logs["items"]:
            st.dataframe(pd.DataFrame(logs["items"]), use_container_width=True)
        else:
            st.info("沒有日誌。")
    except api_client.ApiError as exc:
        st.error(exc.detail)

with tab_db:
    st.subheader("資料庫狀態")
    try:
        status = api_client.get_json("/api/admin/db-status")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("連線", "正常" if status["connected"] else "異常")
        c2.metric("連接池大小", status["pool_size"])
        c3.metric("使用中連線", status["checked_out"])
        c4.metric("延遲 (ms)", status["latency_ms"])
    except api_client.ApiError as exc:
        st.error(exc.detail)

with tab_history:
    st.subheader("即時資料歷史")
    only_anomaly = st.checkbox("僅顯示異常")
    params = {"page": 1, "page_size": 100, "only_anomaly": only_anomaly}
    try:
        hist = api_client.get_json("/api/realtime/history", params=params)
        st.caption(f"共 {hist['total']} 筆")
        if hist["items"]:
            st.dataframe(pd.DataFrame(hist["items"]), use_container_width=True)
        else:
            st.info("沒有資料。")
    except api_client.ApiError as exc:
        st.error(exc.detail)
