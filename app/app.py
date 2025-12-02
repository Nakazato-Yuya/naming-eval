# app/app.py
import sys
import pathlib
import io
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

# 修正: Weights のインポートを削除
from src.features.epi import evaluate_name

st.set_page_config(page_title="Naming-Eval", layout="wide")
st.title("Naming-Eval (EPI + Voiced)")

# ---- Weights（共通）----
st.sidebar.header("合成重み（スライダー）")

# 既存の指標
w_len  = st.sidebar.slider("w_len（長さペナルティ）",  0.0, 1.0, 0.18, 0.01)
w_open = st.sidebar.slider("w_open（開音節不足）",     0.0, 1.0, 0.16, 0.01)
w_sp   = st.sidebar.slider("w_sp（特殊モーラ比）",     0.0, 1.0, 0.16, 0.01)
w_yoon = st.sidebar.slider("w_yoon（拗音比）",         0.0, 1.0, 0.12, 0.01)

# ★新機能：濁音・半濁音
st.sidebar.markdown("---")
st.sidebar.caption("追加指標（力強さ・ポップさ）")
w_voiced = st.sidebar.slider("w_voiced（濁音比）",     0.0, 1.0, 0.00, 0.01, help="ガ行・ダ行などの比率。力強さを評価に入れたい場合は上げてください")
w_semi   = st.sidebar.slider("w_semi（半濁音比）",     0.0, 1.0, 0.00, 0.01, help="パ行の比率。ポップさを評価に入れたい場合は上げてください")

normalize = st.sidebar.checkbox("重みを正規化して合成する（推奨）", value=True)

# 重み辞書の作成
current_weights = {
    "f_len": w_len,
    "f_open": w_open,
    "f_sp": w_sp,
    "f_yoon": w_yoon,
    "f_voiced": w_voiced,
    "f_semi_voiced": w_semi,
}

w_sum = sum(current_weights.values())
if w_sum == 0:
    st.sidebar.warning("重みが全て0です。どれかを上げてください。")
st.sidebar.caption(f"重みの合計: **{w_sum:.2f}**")

tab_single, tab_batch = st.tabs(["🔤 単体評価", "📄 CSVバッチ評価"])

# ---- 単体評価 ----
with tab_single:
    name = st.text_input("名前（かな/カナ/混在OK）", "ガンダム")
    if name:
        r = evaluate_name(name)
        st.write("**正規化カナ**:", r["kana"])
        st.write("**モーラ列**:", " | ".join(r["mora"]))

        # メトリクス表示（2行に分ける）
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("M（モーラ数）", r["M"])
        c2.metric("f_len (長さ)",  round(r["f_len"],  3))
        c3.metric("f_open (開音)", round(r["f_open"], 3))
        c4.metric("f_sp (特殊)",   round(r["f_sp"],   3))
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("f_yoon (拗音)", round(r["f_yoon"], 3))
        c6.metric("f_voiced (濁)", round(r["f_voiced"], 3))
        c7.metric("f_semi (半濁)", round(r["f_semi_voiced"], 3))
        
        # UI重みでの合成
        epi_val = 0.0
        if w_sum > 0:
            numerator = sum(current_weights[k] * r.get(k, 0.0) for k in current_weights)
            epi_val = numerator / w_sum if normalize else numerator
            
        c8.metric("EPI (総合)", round(float(epi_val), 3))

# ---- CSVバッチ評価 ----
with tab_batch:
    st.write("CSVをアップロードすると、現在のスライダーの重みでEPIを再計算します。")
    uploaded = st.file_uploader("CSVをアップロード", type=["csv"])
    
    if uploaded and st.button("スコア計算実行"):
        df_in = pd.read_csv(uploaded)
        
        # DataFrameに対して1行ずつ評価を実行
        results = []
        for _, row in df_in.iterrows():
            # nameカラムがある前提。なければ1列目を使う
            target_name = row.get("name", row.iloc[0])
            res = evaluate_name(str(target_name))
            
            # 重み付きスコアの再計算
            numerator = sum(current_weights[k] * res.get(k, 0.0) for k in current_weights)
            final_epi = numerator / w_sum if (normalize and w_sum > 0) else numerator
            
            # 結果を統合
            res["EPI"] = final_epi
            results.append(res)
            
        df_out = pd.DataFrame(results)
        
        st.subheader("結果プレビュー")
        st.dataframe(df_out)
        
        csv_buf = io.StringIO()
        df_out.to_csv(csv_buf, index=False)
        st.download_button(
            "結果CSVをダウンロード",
            data=csv_buf.getvalue().encode("utf-8"),
            file_name="naming_eval_result.csv",
            mime="text/csv"
        )