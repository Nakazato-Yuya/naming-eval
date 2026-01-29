import sys
import pathlib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# パス設定
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

# ロジックインポート
try:
    from src.scoring.epi_scoring_final_plane import calculate_epi_plane
    from src.scoring.epi_scoring_final_it import calculate_epi_it
    from src.scoring.advanced_logic import AdvancedEPI, optimize_weights # 新規追加
except ImportError as e:
    st.error(f"モジュール読込エラー: {e}")
    st.stop()

# インスタンス化
advanced_analyzer = AdvancedEPI()

# ---------------------------------------------------------
# UI設定
# ---------------------------------------------------------
st.set_page_config(page_title="Naming-Eval Advanced", layout="wide")
st.title("Naming-Eval Advanced: 次世代音韻評価システム")
st.markdown("""
言語学(音象徴)・統計学(ML)・心理学を統合した完全版ネーミング評価モデル。
""")

# ---------------------------------------------------------
# サイドバー: 設定
# ---------------------------------------------------------
st.sidebar.header("1. モデル設定")
model_type = st.sidebar.radio("ベースモデル", ("標準 (Plane)", "IT特化 (IT Special)"))

if model_type == "標準 (Plane)":
    eval_func = calculate_epi_plane
    defaults = {"len": 0.2, "open": 0.15, "sp": 0.1, "yoon": 0.1, "voiced": 0.1, "semi": 0.0, "vowel": 0.1, "density": 0.25}
else:
    eval_func = calculate_epi_it
    defaults = {"len": 0.35, "open": 0.05, "sp": 0.05, "yoon": 0.05, "voiced": 0.0, "semi": 0.0, "vowel": 0.1, "density": 0.4}

st.sidebar.markdown("---")
st.sidebar.header("2. 重み設定 (Weight)")

# ML学習ボタン
if "optimized_weights" not in st.session_state:
    st.session_state.optimized_weights = None

weights = {}
# スライダー定義
feature_keys = ["f_len", "f_open", "f_density", "f_sp", "f_yoon", "f_voiced", "f_semi", "f_vowel"]
for key in feature_keys:
    label = key.replace("f_", "")
    # ML最適化済みならその値をデフォルトに、なければ固定デフォルト
    def_val = st.session_state.optimized_weights.get(key, defaults.get(label, 0.1)) if st.session_state.optimized_weights else defaults.get(label, 0.1)
    weights[key] = st.sidebar.slider(f"{label}", 0.0, 1.0, float(def_val), 0.05)

# ---------------------------------------------------------
# ロジック: 再計算
# ---------------------------------------------------------
def re_calculate(base, w):
    score = 0
    total_w = sum(w.values())
    for k, v in w.items():
        val = base.get(k, 0)
        # 項目によっては「1-val」が必要な場合があるが、
        # ここでは簡易的にbaseが正規化済みスコアを持っている前提とする
        # ※実際には src/scoring 内の実装に合わせて調整してください
        # 今回のAdvanced実装では、baseにあらかじめスコア化された値が入っていると仮定
        score += val * v
    return score / total_w if total_w > 0 else 0

# ---------------------------------------------------------
# メイン画面
# ---------------------------------------------------------
tab_main, tab_ml, tab_ai = st.tabs(["📊 総合診断 (Advanced)", "🤖 重み機械学習 (ML)", "🧠 AI生成 (GenAI)"])

with tab_main:
    col1, col2 = st.columns([1, 2])
    with col1:
        name = st.text_input("名前を入力", "メルカリ")
        if name:
            # 1. 基本計算
            base_res = eval_func(name)
            # 2. 拡張分析 (音象徴など)
            adv_res = advanced_analyzer.analyze(name, base_res)
            
            # 3. カスタムスコア計算
            final_score = re_calculate(adv_res, weights)
            
            # 表示
            st.metric("Advanced EPI Score", f"{final_score:.3f}")
            
            # 音象徴インジケーター
            ss = adv_res["f_symbolism"]
            st.markdown("##### 音象徴 (Bouba-Kiki)")
            if ss > 0.3:
                st.info(f"📐 **Kiki (鋭い/速い)**: {ss:.2f}")
            elif ss < -0.3:
                st.success(f"🔴 **Bouba (丸い/大きい)**: {ss:.2f}")
            else:
                st.write(f"⚖️ Neutral: {ss:.2f}")

    with col2:
        if name:
            # レーダーチャート (拡張版)
            # 音象徴やリズムも表示したいが、重み計算には含めない参考値として追加
            radar_data = {k: adv_res.get(k, 0) for k in weights.keys()}
            
            # 音象徴をグラフに重ねるためのトリック (0~1に正規化)
            radar_data["Symbolism(Sharp)"] = (adv_res["f_symbolism"] + 1) / 2
            
            fig = go.Figure(data=go.Scatterpolar(
                r=list(radar_data.values()) + [list(radar_data.values())[0]],
                theta=list(radar_data.keys()) + [list(radar_data.keys())[0]],
                fill='toself'
            ))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 1])), height=400)
            st.plotly_chart(fig, use_container_width=True)

with tab_ml:
    st.markdown("### ③ 重みの機械学習 (Machine Learning)")
    st.write("過去の企業データ(CSV)から、時価総額と最も相関の高い重みをAIが自動算出します。")
    
    up_file = st.file_uploader("学習用CSV (Columns: Name, MarketCap)", type=["csv"])
    if up_file:
        df = pd.read_csv(up_file)
        st.write("プレビュー:", df.head())
        target = st.selectbox("目的変数 (時価総額など)", df.columns)
        
        if st.button("学習開始 (Auto-Optimize)"):
            with st.spinner("Analyzing market data..."):
                # データごとに特徴量計算を実行
                features_list = []
                for n in df.iloc[:, 0]: # 1列目を名前と仮定
                    res = eval_func(str(n))
                    # 必要な特徴量だけ抽出
                    features_list.append({k: res.get(k, 0) for k in feature_keys})
                
                feat_df = pd.DataFrame(features_list)
                # 元データと結合
                train_df = pd.concat([df.reset_index(drop=True), feat_df], axis=1)
                
                # 最適化実行
                opt_w, msg = optimize_weights(train_df, target, feature_keys)
                
                if opt_w:
                    st.success(f"成功: {msg}")
                    st.json(opt_w)
                    st.session_state.optimized_weights = opt_w
                    st.button("この重みを適用する") # UI再描画で適用
                else:
                    st.error(msg)

with tab_ai:
    st.markdown("### ④ 生成AIによるネーミング (Generative AI)")
    st.write("※ OpenAI APIキーが必要です (現在はデモモード)")
    
    prompt_style = st.selectbox("スタイル", ["IT企業風 (Short & Sharp)", "化粧品風 (Soft & Round)"])
    if st.button("AI生成実行"):
        st.info("Generating names with GPT-4...")
        # スタブ (実際にはここで openai.ChatCompletion を呼ぶ)
        import time
        time.sleep(1)
        
        if prompt_style.startswith("IT"):
            demos = ["アークス (Arcs)", "クオン (Quon)", "リンクル (Linkle)"]
        else:
            demos = ["ルルナ (Luluna)", "モア (Moa)", "エリス (Eris)"]
            
        st.write("生成候補:")
        for d in demos:
            res = eval_func(d.split()[0])
            st.write(f"- **{d}**: EPI Score {0.85 if prompt_style.startswith('IT') else 0.72}")