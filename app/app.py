# app/app.py
import sys
import pathlib
import io
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.features.epi import evaluate_name
from src.scoring.batch_eval import Weights, evaluate_df

st.set_page_config(page_title="Naming-Eval", layout="wide")
st.title("Naming-Eval (EPI)")

# ---- Weights（共通）----
st.sidebar.header("合成重み（スライダー）")
w_len  = st.sidebar.slider("w_len（長さペナルティ）",  0.0, 1.0, 0.18, 0.01)
w_open = st.sidebar.slider("w_open（開音節不足）",     0.0, 1.0, 0.16, 0.01)
w_sp   = st.sidebar.slider("w_sp（特殊モーラ比）",     0.0, 1.0, 0.16, 0.01)
w_yoon = st.sidebar.slider("w_yoon（拗音比）",         0.0, 1.0, 0.12, 0.01)
normalize = st.sidebar.checkbox("重みを正規化して合成する（推奨）", value=True)

w_sum = w_len + w_open + w_sp + w_yoon
if w_sum == 0:
    st.sidebar.warning("重みが全て0です。どれかを上げてください。")
st.sidebar.caption(f"重みの合計: **{w_sum:.2f}**")
weights = Weights(w_len=w_len, w_open=w_open, w_sp=w_sp, w_yoon=w_yoon)

tab_single, tab_batch = st.tabs(["🔤 単体評価", "📄 CSVバッチ評価"])

# ---- 単体評価 ----
with tab_single:
    name = st.text_input("名前（かな/カナ/混在OK）", "サクラ")
    if name:
        r = evaluate_name(name)
        st.write("**正規化カナ**:", r["kana"])
        st.write("**モーラ列**:", " | ".join(r["mora"]))

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("M（モーラ数）", r["M"])
        c2.metric("f_len",  round(r["f_len"],  3))
        c3.metric("f_open", round(r["f_open"], 3))
        c4.metric("f_sp",   round(r["f_sp"],   3))
        c5.metric("f_yoon", round(r["f_yoon"], 3))

        # UI重みでの合成（正規化ONなら総和=1）
        if normalize and w_sum > 0:
            epi_ui = (w_len*r["f_len"] + w_open*r["f_open"] + w_sp*r["f_sp"] + w_yoon*r["f_yoon"]) / w_sum
        else:
            epi_ui = (w_len*r["f_len"] + w_open*r["f_open"] + w_sp*r["f_sp"] + w_yoon*r["f_yoon"])
        st.metric("EPI（UI重み）", round(float(epi_ui), 3))
        st.caption("※ YAMLの重みとは独立に、UIスライダーの値で合成。")

# ---- CSVバッチ評価 ----
with tab_batch:
    st.write("列例: `name`（任意で `f_len,f_open,f_sp,f_yoon` があれば使用。無ければ name から内部計算）")
    uploaded = st.file_uploader("CSVをアップロード", type=["csv"])
    run = st.button("スコアを計算する", type="primary", use_container_width=True)

    if run:
        if uploaded is None:
            st.warning("先にCSVをアップロードしてください。")
        else:
            df_in = pd.read_csv(uploaded)
            df_out = evaluate_df(df_in, weights)

            # 表示用に正規化合成（保存そのものは evaluate_df のままでもOK）
            if normalize and w_sum > 0:
                df_out["EPI"] = (
                    w_len*df_out["f_len"]
                    + w_open*df_out["f_open"]
                    + w_sp*df_out["f_sp"]
                    + w_yoon*df_out["f_yoon"]
                ) / w_sum
                df_out["FinalScore"] = df_out["EPI"]

            st.subheader("結果プレビュー")
            st.dataframe(df_out, use_container_width=True)

            csv_buf = io.StringIO()
            df_out.to_csv(csv_buf, index=False)
            st.download_button(
                "結果CSVをダウンロード",
                data=csv_buf.getvalue().encode("utf-8"),
                file_name="naming_eval_result.csv",
                mime="text/csv",
                use_container_width=True,
            )

st.divider()
st.caption("起動: `PYTHONPATH=. streamlit run app/app.py`")
   