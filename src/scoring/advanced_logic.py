import unicodedata
import numpy as np
import pandas as pd  # 修正: 先頭に移動
from sklearn.linear_model import LinearRegression  # 修正: 先頭に移動

# ---------------------------------------------------------
# 音象徴 (Sound Symbolism) 定義
# ---------------------------------------------------------
# "Kiki" (鋭い) vs "Bouba" (丸い/大きい)
# +1.0 に近いほど Kiki, -1.0 に近いほど Bouba
SHARP_CHARS = set("キキシチニヒミリイエケセテネヘメレフェ")  # イ段、エ段、無声子音系
ROUND_CHARS = set("アクストヌフムユルオコソトノホモヨロワン")  # ウ段、オ段、マ行、ラ行、濁音系
# ※ 厳密には子音と母音の組み合わせだが、簡易的にカナで判定


def calculate_sound_symbolism(kana: str) -> float:
    """
    ブーバ・キキ効果スコアを算出 (-1.0: Round/Large ~ +1.0: Sharp/Small)
    """
    score = 0.0
    count = 0
    for char in kana:
        # 濁音・半濁音の分解
        base_char = unicodedata.normalize('NFD', char)[0]

        # 母音/子音の簡易判定
        if char in SHARP_CHARS or base_char in SHARP_CHARS:
            score += 1.0
        elif char in ROUND_CHARS or base_char in ROUND_CHARS:
            score -= 1.0

        # 濁音は「重さ・大きさ」を表すため Bouba (-0.5) 寄りに加算
        if char in "ガギグゲゴザジズゼゾダヂヅデドバビブベボ":
            score -= 0.5
        # 半濁音は「鋭さ・軽さ」を表すため Kiki (+0.5) 寄りに加算
        if char in "パピプペポ":
            score += 0.5

        count += 1

    if count == 0:
        return 0.0  # 修正: 改行を入れた

    # -1.0 ~ 1.0 にクリップ
    return max(-1.0, min(1.0, score / count))


# ---------------------------------------------------------
# 拡張分析クラス
# ---------------------------------------------------------
class AdvancedEPI:
    def __init__(self):
        # 将来的にN-gramデータやアクセント辞書をロードする場所
        self.ngram_model = None
        self.accent_dict = None

    def get_ngram_score(self, moras: list) -> float:
        """
        ① モーラN-gram (3-gram) による自然性スコア
        現状: データがないため、簡易的な「不自然な連続」ペナルティのみ実装
        """
        # スタブ実装: 同じ母音の3連続などは不自然としてペナルティ
        score = 1.0
        if len(moras) >= 3:
            # 簡易ロジック: 全く同じ音が3回続くと違和感 (例: ラララ)
            for i in range(len(moras) - 2):
                if moras[i] == moras[i+1] == moras[i+2]:
                    score -= 0.3
        return max(0.0, score)

    def get_accent_score(self, kana: str) -> float:
        """
        ② アクセント評価 (リズム感)
        現状: 辞書がないため、長音・促音の位置からリズムの良し悪しを簡易推定
        """
        score = 0.5  # 中立
        # 末尾が長音・撥音で終わるのはリズムが良いことが多い (平板/安定)
        if kana.endswith("ー") or kana.endswith("ン"):
            score += 0.2
        # 4文字で2文字目にッがある (例: ネット) -> 頭高/中高のインパクト
        if len(kana) == 4 and kana[1] == "ッ":
            score += 0.3
        return min(1.0, score)

    def analyze(self, name: str, base_epi_result: dict) -> dict:
        """
        既存のEPI結果にアドバンスド指標を追加統合
        """
        kana = base_epi_result.get("kana", name)  # カナ取得

        # 1. 音象徴 (Bouba-Kiki)
        ss_score = calculate_sound_symbolism(kana)

        # 2. N-gram (自然性)
        # モーラ分解は簡易的に文字単位とする（厳密なモーラ分解は既存ロジック依存）
        ngram_score = self.get_ngram_score(list(kana))

        # 3. アクセント (リズム)
        accent_score = self.get_accent_score(kana)

        # 結果統合
        base_epi_result.update({
            "f_symbolism": ss_score,  # -1(丸) ~ +1(鋭)
            "f_natural": ngram_score,
            "f_rhythm": accent_score
        })
        return base_epi_result


# ---------------------------------------------------------
# 機械学習: 重み最適化 (Machine Learning)
# ---------------------------------------------------------
def optimize_weights(df: pd.DataFrame, target_col: str, feature_cols: list):
    """
    ③ 重みの機械学習
    IPOデータ等のDataFrameを受け取り、時価総額(target)を目的変数、
    音韻特徴量(features)を説明変数として線形回帰を行い、最適な重み係数を返す。
    """
    # 欠損除去
    df_clean = df.dropna(subset=feature_cols + [target_col])

    if len(df_clean) < 10:
        return None, "データ不足(10件以上必要)"

    X = df_clean[feature_cols]
    y = df_clean[target_col]

    model = LinearRegression()
    model.fit(X, y)

    # 係数を正規化して重みとして返す
    raw_weights = model.coef_
    # 負の係数（時価総額を下げる要素）は重みを0にするか、ロジックに合わせて反転
    # ここでは「寄与度」の絶対値を重みのベースとする簡易実装
    abs_weights = np.abs(raw_weights)
    total = np.sum(abs_weights)

    if total == 0:
        return None, "有効な相関が見つかりませんでした"  # 修正: 改行を入れた

    optimized_weights = {col: w/total for col, w in zip(feature_cols, abs_weights)}
    score = model.score(X, y)  # R^2スコア

    return optimized_weights, f"学習完了 (R2={score:.3f})"