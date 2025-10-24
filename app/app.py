import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import streamlit as st
from src.features.epi import evaluate_name

st.title("Naming-Eval (EPI demo)")
name = st.text_input("名前（かな/カナ/混在OK）", "サクラ")
if name:
    r = evaluate_name(name)
    st.write("**正規化カナ**:", r["kana"])
    st.write("**モーラ列**:", " | ".join(r["mora"]))
    st.metric("M（モーラ数）", r["M"])
    st.metric("f_len（長さペナルティ）", round(r["f_len"], 3))
    st.metric("f_open（開音節不足）", round(r["f_open"], 3))
    st.metric("f_sp（特殊モーラ比）", round(r["f_sp"], 3))
    st.metric("f_yoon（拗音比）", round(r["f_yoon"], 3))
    st.metric("EPI（合成スコア）", round(r["EPI"], 3))
