# --- app/app.py ---
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import streamlit as st
from src.features.epi import evaluate_name

st.title("Naming-Eval (EPI demo)")

# 入力欄
name = st.text_input("名前（かな/カナ/混在OK）", "サクラ")

# 重みスライダー（UIで合成重みを調整）
st.subheader("合成重み（インタラクティブ）")
w_len  = st.slider("w: f_len（長さペナルティ）",  0.0, 1.0, 0.18, 0.01)
w_open = st.slider("w: f_open（開音節不足）",     0.0, 1.0, 0.16, 0.01)
w_sp   = st.slider("w: f_sp（特殊モーラ比）",     0.0, 1.0, 0.16, 0.01)
w_yoon = st.slider("w: f_yoon（拗音比）",         0.0, 1.0, 0.12, 0.01)

if name:
    r = evaluate_name(name)

    # 個別指標の表示
    st.write("**正規化カナ**:", r["kana"])
    st.write("**モーラ列**:", " | ".join(r["mora"]))
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("M（モーラ数）", r["M"])
    col2.metric("f_len",  round(r["f_len"],  3))
    col3.metric("f_open", round(r["f_open"], 3))
    col4.metric("f_sp",   round(r["f_sp"],   3))
    col5.metric("f_yoon", round(r["f_yoon"], 3))

    # UI重みでの合成EPI（YAMLの重みとは独立）
    wsum = w_len + w_open + w_sp + w_yoon or 1.0
    epi_ui = (w_len*r["f_len"] + w_open*r["f_open"] + w_sp*r["f_sp"] + w_yoon*r["f_yoon"]) / wsum

    st.metric("EPI（UI重み）", round(epi_ui, 3))
    st.caption("※ YAMLの重みとは独立に、UIのスライダーで合成値を再計算しています。")

st.divider()
st.caption("起動例: `PYTHONPATH=. streamlit run app/app.py`")
