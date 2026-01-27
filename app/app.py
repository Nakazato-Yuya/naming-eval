import sys
import pathlib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# プロジェクトルートをパスに追加して src をインポート可能にする
# (現在のファイル app/app.py の2つ上の階層をパスに追加)
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------
# ロジックのインポート
# ---------------------------------------------------------
try:
    from src.scoring.epi_scoring_final_plane import calculate_epi_plane
    from src.scoring.epi_scoring_final_it import calculate_epi_it
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.warning("ディレクトリ構成が正しいか確認してください。(app/ と src/ が同じ階層にある必要があります)")
    st.stop()

# ---------------------------------------------------------
# UI設定
# ---------------------------------------------------------
st.set_page_config(page_title="Naming-Eval (Latest)", layout="wide")
st.title("Naming-Eval: 音韻適性評価システム")
st.markdown("社名・サービス名の「音の響き」を定量評価します。")

# ---------------------------------------------------------
# サイドバー: モデル選択
# ---------------------------------------------------------
st.sidebar.header("評価モデル設定")

model_type = st.sidebar.radio(
    "使用する評価モデル",
    ("標準モデル (Plane)", "IT特化モデル (IT Special)"),
    index=0,
    help="標準モデル: 一般的な美しさ / IT特化モデル: 濁音や専門用語を肯定的に評価"
)

# 選択されたモデルに応じて関数を切り替え
if model_type == "標準モデル (Plane)":
    eval_func = calculate_epi_plane
    st.sidebar.info("✨ **標準モデル**\n\n濁音が少なく、母音で終わる明るい響きを高評価します。\n一般消費者向けブランドに適しています。")
else:
    eval_func = calculate_epi_it
    st.sidebar.success("💻 **IT特化モデル**\n\n濁音（力強さ）や閉音節（テック感）を減点せず、\n長さ（冗長性）を厳しく評価します。\nBtoBやテック企業に適しています。")

# ---------------------------------------------------------
# レーダーチャート描画関数
# ---------------------------------------------------------
def plot_radar(res_dict):
    # 表示したい指標（スコア以外）
    categories = ['f_len', 'f_open', 'f_sp', 'f_yoon', 'f_voiced', 'f_vowel', 'f_density']
    # 日本語ラベルへのマッピング
    labels = ['長さ', '開放感', '特殊音', '単純性', '清音性/濁音', '母音多様', '密度']
    
    values = [res_dict.get(c, 0.0) for c in categories]
    
    # グラフを閉じるために最初の値を最後に追加
    values += [values[0]]
    labels_closure = labels + [labels[0]]

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=labels_closure,
        fill='toself',
        name='Features'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=False,
        margin=dict(t=20, b=20, l=40, r=40)
    )
    return fig

# ---------------------------------------------------------
# メインコンテンツ
# ---------------------------------------------------------
tab_single, tab_batch = st.tabs(["🔤 単体評価 (Playground)", "📄 CSV一括診断"])

# ---- Tab 1: 単体評価 ----
with tab_single:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        name_input = st.text_input("名前を入力してください", "任天堂")
        if st.button("診断する", type="primary"):
            if name_input:
                # 計算実行
                result = eval_func(name_input)
                
                st.markdown("---")
                # 総合スコア表示
                score = result["EPI_Score"]
                
                # スコアに応じた色付け
                if score >= 0.8:
                    st.success(f"### 総合評価: S ({score:.3f})")
                elif score >= 0.6:
                    st.info(f"### 総合評価: A ({score:.3f})")
                elif score >= 0.4:
                    st.warning(f"### 総合評価: B ({score:.3f})")
                else:
                    st.error(f"### 総合評価: C ({score:.3f})")
                
                st.metric("モーラ数 (拍数)", result["M"])
                
                # 詳細データ
                st.write("詳細スコア:")
                st.json(result, expanded=False)

    with col2:
        if name_input:
            # 再計算して表示
            result = eval_func(name_input)
            st.subheader("音韻特性レーダーチャート")
            st.plotly_chart(plot_radar(result), use_container_width=True)

# ---- Tab 2: CSVバッチ評価 ----
with tab_batch:
    st.markdown("### CSVファイル一括診断")
    st.write("企業名・サービス名が入ったCSVをアップロードすると、選択中のモデルで一括採点します。")
    
    uploaded_file = st.file_uploader("CSVファイルをアップロード", type=["csv"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("プレビュー:", df.head())
            
            # 名前が入っているカラムを選択
            target_col = st.selectbox("評価する名前のカラムを選択してください", df.columns)
            
            if st.button("一括計算実行"):
                with st.spinner("計算中..."):
                    # プログレスバー
                    progress_bar = st.progress(0)
                    results_list = []
                    
                    for i, row in df.iterrows():
                        name_val = str(row[target_col])
                        res = eval_func(name_val)
                        res["input_name"] = name_val # 元の名前を保持
                        results_list.append(res)
                        progress_bar.progress((i + 1) / len(df))
                    
                    # 結果をDataFrame化
                    df_res = pd.DataFrame(results_list)
                    
                    # 元のデータと結合
                    final_df = pd.concat([df.reset_index(drop=True), df_res], axis=1)
                    
                    st.success("計算完了！")
                    st.dataframe(final_df.head())
                    
                    # ダウンロードボタン
                    csv = final_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="結果CSVをダウンロード",
                        data=csv,
                        file_name=f"epi_results_{model_type}.csv",
                        mime='text/csv',
                    )
                    
                    # 分布の可視化
                    st.subheader("スコア分布")
                    st.bar_chart(final_df["EPI_Score"])
                    
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")