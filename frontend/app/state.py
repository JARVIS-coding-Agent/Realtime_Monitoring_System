"""Streamlit session 狀態管理：登入狀態、token、角色。"""
import streamlit as st


def init_state() -> None:
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("username", None)


def set_auth(token: str, role: str, username: str) -> None:
    st.session_state["token"] = token
    st.session_state["role"] = role
    st.session_state["username"] = username


def clear_auth() -> None:
    st.session_state["token"] = None
    st.session_state["role"] = None
    st.session_state["username"] = None


def is_authenticated() -> bool:
    return bool(st.session_state.get("token"))


def get_token() -> str | None:
    return st.session_state.get("token")


def get_role() -> str | None:
    return st.session_state.get("role")


def require_login() -> bool:
    """在子頁面呼叫；未登入時顯示提示並回傳 False。"""
    init_state()
    if not is_authenticated():
        st.warning("請先至首頁登入。")
        st.stop()
    return True
