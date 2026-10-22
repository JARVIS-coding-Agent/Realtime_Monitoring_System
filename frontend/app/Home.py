"""Streamlit 入口：登入 / 登出。"""
import streamlit as st

import api_client
from state import clear_auth, get_role, init_state, is_authenticated, set_auth

st.set_page_config(page_title="即時監控系統", page_icon="📊", layout="wide")

init_state()

st.title("📊 即時資料分析與監控系統")

if is_authenticated():
    st.success(f"已登入：{st.session_state.get('username')}（角色：{get_role()}）")
    st.write("請使用左側選單進入各功能頁面：即時監控、資料管理、資料分析、系統管理。")
    if st.button("登出"):
        clear_auth()
        st.rerun()
else:
    tab_login, tab_register = st.tabs(["登入", "註冊"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("帳號")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("登入")
        if submitted:
            try:
                result = api_client.login(username, password)
                set_auth(result["access_token"], result["role"], username)
                st.success("登入成功")
                st.rerun()
            except api_client.ApiError as exc:
                st.error(f"登入失敗：{exc.detail}")

    with tab_register:
        with st.form("register_form"):
            r_username = st.text_input("帳號", key="r_user")
            r_email = st.text_input("電子郵件", key="r_email")
            r_password = st.text_input("密碼（至少 8 碼）", type="password", key="r_pass")
            r_submitted = st.form_submit_button("註冊")
        if r_submitted:
            try:
                api_client.register(r_username, r_email, r_password)
                st.success("註冊成功，請切換到登入分頁登入。")
            except api_client.ApiError as exc:
                st.error(f"註冊失敗：{exc.detail}")

    st.info(
        "測試帳號（預設）：\n\n"
        "- admin / Admin@12345（管理員）\n"
        "- user / User@12345（一般使用者）\n"
        "- viewer / Viewer@12345（檢視者）"
    )
