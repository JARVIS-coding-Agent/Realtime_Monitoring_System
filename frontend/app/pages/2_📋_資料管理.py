"""資料管理頁：CRUD、分頁/篩選/排序、批量導入。"""
import pandas as pd
import streamlit as st

import api_client
from state import get_role, require_login

require_login()

st.set_page_config(page_title="資料管理", page_icon="📋", layout="wide")
st.title("📋 資料管理")

role = get_role()
can_write = role in ("admin", "user")

# === 查詢 ===
st.subheader("資料列表")
c1, c2, c3, c4 = st.columns(4)
with c1:
    category = st.text_input("分類篩選", "")
with c2:
    sort_by = st.selectbox("排序欄位", ["timestamp", "created_at", "value"])
with c3:
    order = st.selectbox("排序", ["desc", "asc"])
with c4:
    page = st.number_input("頁次", min_value=1, value=1, step=1)

params = {"page": int(page), "page_size": 20, "sort_by": sort_by, "order": order}
if category:
    params["category"] = category

try:
    data = api_client.get_json("/api/data", params=params)
    st.caption(f"共 {data['total']} 筆")
    if data["items"]:
        st.dataframe(pd.DataFrame(data["items"]), use_container_width=True)
    else:
        st.info("沒有資料。")
except api_client.ApiError as exc:
    st.error(exc.detail)

# === 建立 ===
if can_write:
    st.subheader("建立資料")
    with st.form("create_form"):
        title = st.text_input("標題")
        value = st.number_input("數值", value=0.0)
        cat = st.text_input("分類")
        submitted = st.form_submit_button("建立")
    if submitted:
        try:
            api_client.post_json(
                "/api/data", {"title": title, "value": value, "category": cat}
            )
            st.success("建立成功")
            st.rerun()
        except api_client.ApiError as exc:
            st.error(exc.detail)

    # === 更新 / 刪除 ===
    st.subheader("更新 / 刪除")
    rid = st.number_input("資料 ID", min_value=1, step=1, key="mod_id")
    mc1, mc2 = st.columns(2)
    with mc1:
        with st.form("update_form"):
            u_value = st.number_input("新數值", value=0.0, key="u_val")
            u_submit = st.form_submit_button("更新數值")
        if u_submit:
            try:
                api_client.put_json(f"/api/data/{int(rid)}", {"value": u_value})
                st.success("更新成功")
            except api_client.ApiError as exc:
                st.error(exc.detail)
    with mc2:
        if st.button("刪除此筆"):
            try:
                api_client.delete(f"/api/data/{int(rid)}")
                st.success("刪除成功")
            except api_client.ApiError as exc:
                st.error(exc.detail)

    # === 批量導入 ===
    st.subheader("批量導入（CSV / JSON）")
    uploaded = st.file_uploader("選擇檔案", type=["csv", "json"])
    if uploaded is not None and st.button("開始導入"):
        try:
            result = api_client.upload_file("/api/data/import", uploaded.name, uploaded.getvalue())
            st.success(f"成功 {result['success_count']} 筆，失敗 {result['failed_count']} 筆")
            if result["errors"]:
                st.dataframe(pd.DataFrame(result["errors"]), use_container_width=True)
        except api_client.ApiError as exc:
            st.error(exc.detail)
else:
    st.info("檢視者僅能瀏覽資料。")
