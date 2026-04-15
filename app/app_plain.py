import sys
import pathlib
import streamlit as st
import plotly.graph_objects as go

# パス設定
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

try:
    from src.scoring._legacy_epi_scoring_final_plane import calculate_epi_plane
except ImportError:
    st.error("モジュールが見つかりません。")
    st.stop()

# ---------------------------------------------------------
# ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="Naming-Eval Lite", layout="centered")

st.title("Naming-Eval Lite 🚀")
st.caption("音韻適性評価システム (Standard Model MVP)")

st.markdown("""
### その名前、言いやすい？
社名やサービス名の「発音のしやすさ」をAIが診断します。
""")

# ---------------------------------------------------------
# 入力エリア
# ---------------------------------------------------------
name_input = st.text_input("診断したい名前（カタカナ推奨）", "メルカリ")

# ---------------------------------------------------------
# 診断ロジック & 表示
# ---------------------------------------------------------
if st.button("診断する", type="primary"):
    if name_input:
        # 1. 計算実行
        result = calculate_epi_plane(name_input)
        score = result["EPI_Score"]
        
        # 2. メインスコア表示
        st.divider()
        st.markdown("### 📊 総合診断結果")
        
        col_score, col_rank = st.columns([1.5, 2])
        
        with col_score:
            st.metric(label="EPI Score", value=f"{score:.3f}")
        
        with col_rank:
            if score >= 0.8:
                st.success("🏆 **Sランク: 非常に発音しやすい！**\n\n覚えやすく、広まりやすい音の響きです。")
            elif score >= 0.6:
                st.info("✨ **Aランク: バランスが良い**\n\n標準的で安定感のある名前です。")
            elif score >= 0.4:
                st.warning("⚠️ **Bランク: 個性的**\n\n少し言いづらさがありますが、フックにはなります。")
            else:
                st.error("🚨 **Cランク: 改善の余地あり**\n\n発音のリズムや長さを見直すと良くなるかもしれません。")

        # 3. レーダーチャート
        categories = ['長さ適正', '開放感', '特殊音なし', '単純性', '清音性', '母音多様', '密度適正']
        keys = ['f_len', 'f_open', 'f_sp', 'f_yoon', 'f_voiced', 'f_vowel', 'f_density']
        values = [result.get(k, 0) for k in keys]
        
        # チャートを閉じる処理
        values_chart = values + [values[0]]
        categories_chart = categories + [categories[0]]
        
        # ★変更点: チャート上に数値を表示するためのテキストを作成
        text_values = [f"{v:.2f}" for v in values_chart]

        fig = go.Figure(data=go.Scatterpolar(
            r=values_chart,
            theta=categories_chart,
            fill='toself',
            line_color='#00CC96',
            # ★変更点: 数値テキストを表示
            text=text_values,
            mode='lines+markers+text',
            textposition="top center"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False,
            height=300, # 少し大きくしました
            margin=dict(t=30, b=30, l=40, r=40)
        )
        st.plotly_chart(fig, use_container_width=True)

        # 4. 詳細パラメータ解説
        st.markdown("### 📝 詳細スコア内訳")
        st.write("各項目の数値（0.0〜1.0）と、その評価理由です。")

        # 項目の定義と解説テキスト
        details = [
            ("f_len", "長さの適正", "2〜4モーラ（拍）が最も覚えやすいとされます。", "長すぎ・短すぎないか"),
            ("f_open", "開放感", "母音（アイウエオ）や「ン」で終わる音の割合。", "明るく聞こえるか"),
            ("f_sp", "特殊音の少なさ", "「ッ」「ー」などの特殊拍が少ないほどスムーズ。", "リズムが詰まらないか"),
            ("f_yoon", "単純性", "「キャ」「シュ」などの拗音が少ないほど単純。", "発音しやすいか"),
            ("f_voiced", "清音性", "濁音（ガザダバ行）が少ないほどクリアな響き。", "音が重くないか"),
            ("f_vowel", "母音の多様性", "使われている母音の種類が多いほど単調にならない。", "音が豊かか"),
            ("f_density", "密度の適正", "音の詰め込み具合が適切か。", "早口になりにくいか")
        ]

        # 2列で詳細を表示
        d_col1, d_col2 = st.columns(2)
        
        for i, (key, label, desc, short_desc) in enumerate(details):
            val = result.get(key, 0)
            target_col = d_col1 if i % 2 == 0 else d_col2
            
            with target_col:
                # ★変更点: タイトル横に数値を太字で表示
                st.markdown(f"**{label}** : `{val:.3f}`")
                st.progress(val)
                st.caption(f"{desc}")
                st.write("") # スペース調整

        st.divider()
        st.caption(f"正規化カナ: {result['kana']} | モーラ数: {result['M']}")