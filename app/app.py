import sys
import pathlib
import io

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

try:
    from src.features.phonology import evaluate_phonology, is_generic
    from src.scoring.features import kana_to_moras, to_hira
except ImportError as e:
    st.error(f"モジュール読込エラー: {e}")
    st.stop()

# ─────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────
st.set_page_config(page_title="Naming-Eval 3軸評価", layout="wide")
st.title("Naming-Eval: 3軸ネーミング評価システム")
st.caption("発音容易性（A軸）・音韻パターン性（B軸）・印象・方向性（C軸）")
st.info("⚠️ このツールは **音韻のみ** を評価します。意味・独自性・商標的差別化は評価対象外です。", icon=None)

# ─────────────────────────────────────────
# サイドバー: 入力 & 重み設定
# ─────────────────────────────────────────
with st.sidebar:
    st.header("名前を入力")
    name_input = st.text_input("カタカナ推奨", "メルカリ", key="name_input")

    st.markdown("---")

    with st.expander("重み設定", expanded=False):
        st.markdown("**軸A（発音容易性）**")
        w_a_len  = st.slider("a_len  （長さ適正）",  0.0, 1.0, 0.35, 0.05)
        w_a_open = st.slider("a_open （開音節比率）", 0.0, 1.0, 0.30, 0.05)
        w_a_sp   = st.slider("a_sp   （特殊音少なさ）",0.0, 1.0, 0.20, 0.05)
        w_a_yoon = st.slider("a_yoon （拗音少なさ）", 0.0, 1.0, 0.15, 0.05)

        st.markdown("**軸B（記憶容易性）**")
        w_b_rhythm = st.slider("b_rhythm（母音リズム）", 0.0, 1.0, 0.50, 0.05)
        w_b_vowel  = st.slider("b_vowel （母音調和）",   0.0, 1.0, 0.50, 0.05)

        st.markdown("**軸間比率**")
        w_axis_a = st.slider("A軸の比重", 0.0, 1.0, 0.70, 0.05)
        w_axis_b = st.slider("B軸の比重", 0.0, 1.0, 0.30, 0.05)


def _calc(name: str) -> dict:
    """名前を評価して、カスタム重みで axis を再計算して返す。"""
    r = evaluate_phonology(name)

    # カスタム重みで axis_a を再計算
    sum_a = w_a_len + w_a_open + w_a_sp + w_a_yoon
    if sum_a > 0:
        r["axis_a"] = (
            w_a_len  * r["a_len"]
            + w_a_open * r["a_open"]
            + w_a_sp   * r["a_sp"]
            + w_a_yoon * r["a_yoon"]
        ) / sum_a

    # カスタム重みで axis_b を再計算
    sum_b = w_b_rhythm + w_b_vowel
    if sum_b > 0:
        r["axis_b"] = (
            w_b_rhythm * r["b_rhythm"]
            + w_b_vowel  * r["b_vowel"]
        ) / sum_b

    # display 更新
    r["axis_a_display"] = int(round(r["axis_a"] * 100))
    r["axis_b_display"] = int(round(r["axis_b"] * 100))

    return r


# ─────────────────────────────────────────
# 評価
# ─────────────────────────────────────────
if not name_input.strip():
    st.info("サイドバーに名前を入力してください。")
    st.stop()

r = _calc(name_input.strip())

# 汎用語警告
if is_generic(name_input.strip()):
    st.warning(
        f"「{name_input.strip()}」は一般名詞（汎用語）と判定されました。"
        " 音韻スコアが高くても、ブランド名としての固有性・差別化・商標登録可能性は別途確認が必要です。"
    )

# ─────────────────────────────────────────
# 4タブ
# ─────────────────────────────────────────
tab_a, tab_b, tab_c, tab_batch = st.tabs([
    "🎵 発音容易性（A軸）",
    "🔊 音韻パターン性（B軸）",
    "🎨 印象・方向性（C軸）",
    "📋 バッチ評価",
])

# ─────── タブ A ───────
with tab_a:
    st.metric("軸A スコア", f"{r['axis_a_display']} / 100")
    st.progress(r["axis_a"])

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)

    metrics_a = [
        (c1, "a_len",  "長さ適正",   "2〜4モーラが最適。ガウス減衰で評価。"),
        (c2, "a_open", "開音節比率", "母音で終わるモーラの割合。高いほど発音しやすい。"),
        (c3, "a_sp",   "特殊音少なさ","ッ・ン が少ないほど高スコア（ーはペナルティなし）。"),
        (c4, "a_yoon", "拗音少なさ", "キャ・シュ などの拗音が少ないほど高スコア。"),
    ]
    for col, key, label, desc in metrics_a:
        with col:
            val = r[key]
            st.markdown(f"**{label}**")
            st.progress(val)
            st.caption(f"{val:.2f} — {desc}")

    st.markdown("---")
    # レーダーチャート
    cats = ["a_len", "a_open", "a_sp", "a_yoon"]
    vals = [r[k] for k in cats] + [r[cats[0]]]
    fig_a = go.Figure(go.Scatterpolar(
        r=vals,
        theta=cats + [cats[0]],
        fill="toself",
        line_color="#00CC96",
        text=[f"{v:.2f}" for v in vals],
        mode="lines+markers+text",
        textposition="top center",
    ))
    fig_a.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        height=320,
        margin=dict(t=30, b=30, l=40, r=40),
    )
    st.plotly_chart(fig_a, use_container_width=True)

# ─────── タブ B ───────
with tab_b:
    st.metric("軸B スコア（音韻パターン性）", f"{r['axis_b_display']} / 100")
    st.progress(r["axis_b"])
    st.caption("b_rhythm（リズム規則性）と b_vowel（母音調和）の加重平均。"
               "「覚えやすさ」そのものではなく、音韻的パターンの強さを示します。")

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        val = r["b_rhythm"]
        st.markdown("**b_rhythm — リズム規則性**")
        st.progress(val)
        st.caption(
            f"{val:.2f} — 隣接母音が同じ（AAAA型）または周期2パターン（ABAB・ABA型）"
            "で高スコア。パナマ[a,a,a]=1.0、サクラ[a,u,a]=1.0、メルカリ[e,u,a,i]=0.0。"
        )

    with c2:
        val = r["b_vowel"]
        st.markdown("**b_vowel — 母音調和**")
        st.progress(val)
        st.caption(
            f"{val:.2f} — 前舌母音{{i,e}}または後舌母音{{u,o,a}}に偏るほど高スコア。"
            "0.5 = 前舌・後舌が均等（最低値）。"
        )

    # 母音列ビジュアライズ
    st.markdown("---")
    st.markdown("**母音の流れ**")
    mora_vowels = []
    moras = kana_to_moras(to_hira(r.get("kana", r["name"])))
    for m in moras:
        v = m.vowel if m.vowel else ("ん" if m.surface == "ん" else "—")
        mora_vowels.append(f"`{m.surface}` ({v})")
    st.markdown(" → ".join(mora_vowels) if mora_vowels else "（解析できませんでした）")

# ─────── タブ C ───────
with tab_c:
    st.info(
        "C軸は印象・方向性の参考指標です。合計スコア（A・B軸）には反映されません。\n\n"
        "⚠️ c_sharpness は **母音のみ** の評価です（子音の影響は未考慮）。"
        "例: スター[u,a] は後舌母音優位で Bouba 寄りと判定されますが、"
        "実際の発音印象は子音 s・t の影響で Kiki 寄りに感じられます。"
    )

    st.markdown("---")
    col_str, col_sharp, col_flu = st.columns(3)

    with col_str:
        val = r["c_strength"]
        st.markdown("**強さ / 濁音比率**")
        st.caption("清音 ←→ 濁音")
        st.progress(val)
        st.caption(f"{val:.2f}")

    with col_sharp:
        val_raw = r["c_sharpness"]
        val_norm = (val_raw + 1) / 2  # [-1,+1] → [0,1]
        st.markdown("**Bouba ←→ Kiki**")
        st.caption("丸い・大きい ←→ 鋭い・小さい")
        st.progress(val_norm)
        st.caption(f"{val_raw:+.2f}（正=Kiki寄り、負=Bouba寄り）")

    with col_flu:
        val = r["c_fluency"]
        st.markdown("**滑らかさ / 共鳴音比率**")
        st.caption("硬い ←→ 滑らか")
        st.progress(val)
        st.caption(f"{val:.2f}")

    st.markdown("---")
    # 軸C 合計スコアに含めない理由の補足
    with st.expander("C軸の解釈について"):
        st.markdown("""
- **c_strength（濁音比率）**: ガ・ザ・ダ・バ行の割合。高いほど重厚感・力強さ。
- **c_sharpness（Kiki-Bouba）**: 前舌母音（イ・エ）多→Kiki（鋭い）、後舌母音（ア・ウ・オ）多→Bouba（丸い）。
- **c_fluency（共鳴音比率）**: ナ・マ・ラ行・ン・ーの割合。高いほど流れるような響き。

これらは「良し悪し」ではなく、ブランドの**方向性・印象の傾向**を示します。
        """)

# ─────── タブ バッチ ───────
with tab_batch:
    st.markdown("### 複数名を一括評価")
    names_text = st.text_area(
        "名前を1行1件で入力（最大200件）",
        "トヨタ\nソニー\nメルカリ\nキャラメル\nシステム",
        height=160,
    )

    if st.button("評価実行", type="primary"):
        names = [n.strip() for n in names_text.splitlines() if n.strip()][:200]
        if not names:
            st.warning("名前を入力してください。")
        else:
            rows = []
            for nm in names:
                res = _calc(nm)
                rows.append({
                    "name":        res["name"],
                    "axis_a":      round(res["axis_a"], 3),
                    "axis_b":      round(res["axis_b"], 3),
                    "c_strength":  round(res["c_strength"], 3),
                    "c_sharpness": round(res["c_sharpness"], 3),
                    "c_fluency":   round(res["c_fluency"], 3),
                    "M":           res["M"],
                    "mora_str":    res["mora_str"],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)

            # CSV ダウンロード
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False, encoding="utf-8")
            st.download_button(
                "CSVダウンロード",
                data=csv_buf.getvalue().encode("utf-8"),
                file_name="naming_eval_batch.csv",
                mime="text/csv",
            )
