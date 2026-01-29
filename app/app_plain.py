import sys
import pathlib
import streamlit as st
import plotly.graph_objects as go

# パスを通す
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

try:
    from src.scoring.epi_scoring_final_plane import calculate_epi_plane
except ImportError:
    st.error("モジュールが見つかりません。ディレクトリ構成を確認してください。")
    st.stop()

# ページ設定
st.set_page_config(page_title="Naming-Eval (Lite)", layout="centered")

st.title("Naming-Eval Lite")
st.markdown("### その名前、言いやすい？")
st.markdown("社名やサービス名の「発音のしやすさ」をAIが診断します。")

# 入力フォーム
name = st.text_input("診断したい名前（カタカナ推奨）", "メルカリ")

if st.button("診断する", type="primary"):
    if name:
        # 計算実行
        result = calculate_epi_plane(name)
        score = result["EPI_Score"]

        # 結果表示
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.metric("総合評価スコア", f"{score:.3f}")
            if score >= 0.8:
                st.success("Sランク: 非常に発音しやすい！")
            elif score >= 0.6:
                st.info("Aランク: バランスが良い")
            else:
                st.warning("Bランク: 個性的・少し難しい")

        with col2:
            # レーダーチャート
            categories = ['f_len', 'f_open', 'f_sp', 'f_yoon', 'f_voiced', 'f_vowel', 'f_density']
            labels = ['長さ', '開放感', '特殊音', '単純性', '清音性', '母音多様', '密度']
            values = [result.get(k, 0) for k in categories]
            # 閉じる処理
            values += [values[0]]
            labels += [labels[0]]

            fig = go.Figure(data=go.Scatterpolar(
                r=values, theta=labels, fill='toself', line_color='#00CC96'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=False,
                height=250,
                margin=dict(t=20, b=20, l=30, r=30)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        st.caption("※標準モデル（Plane）で評価しています。")