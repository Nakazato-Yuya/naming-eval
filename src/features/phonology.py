# -*- coding: utf-8 -*-
"""
src/features/phonology.py

3軸音韻評価モジュール（naming-eval の単一の真実のソース）

Axes
----
A: 発音容易性 (Phonological Ease)   — 高いほど発音しやすい [0, 1]
B: 音韻パターン性 (Phonetic Pattern) — 高いほどパターンが強い [0, 1]
   ※「記憶容易性」は指標の実態と乖離するため改称。
     b_rhythm・b_vowel は音韻の規則性・調和を測定しており、
     記憶しやすさそのものではなく音韻的パターン強度を表す。
C: 印象・方向性 (Brand Impression)  — 合計せず個別表示のみ
     c_strength:  [0, 1]
     c_sharpness: [-1, +1]  ← 合計スコアに含めない（母音のみ評価）
     c_fluency:   [0, 1]

Public API
----------
evaluate_phonology(name, weights=None) -> dict
load_phonology_weights(path="configs/weights.yaml") -> dict
is_generic(name: str) -> bool   ← 汎用語フラグ（音韻評価の限界通知用）

個別指標関数（テスト・外部利用向け）
a_len, a_open, a_sp, a_yoon
b_rhythm, b_vowel
c_strength, c_sharpness, c_fluency

スコープ上の注意
--------------
このモジュールは **音韻** のみを評価します。
以下は評価対象外です:
  - 意味・語義・連想イメージ
  - 独自性・商標的差別化
  - カテゴリ適合性（IT/食品/医療など）
  - 感情的な印象（c_sharpness は母音のみ、子音を無視）
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Mora dataclass と変換関数を借用（src/scoring/features.py は変更しない）
from src.scoring.features import Mora, kana_to_moras, to_hira

# ================================================
# 定数
# ================================================

_A_LEN_MU_LO: int   = 2
_A_LEN_MU_HI: int   = 4
_A_LEN_SIGMA: float = 2.0

_SOKUON_HIRA   = "っ"    # 促音
_MORAIC_N_HIRA = "ん"    # 撥音
_CHOON         = "ー"    # 長音 (U+30FC)

# 濁音（が行・ざ行・だ行・ば行・ゔ）のひらがな先頭文字
_VOICED_HIRA_INITIALS: frozenset = frozenset(
    "がぎぐげござじずぜぞだぢづでどばびぶべぼゔ"
)

# 共鳴音（ナ行・マ行・ラ行）のひらがな先頭文字
_RESONANT_HIRA_INITIALS: frozenset = frozenset(
    "なにぬねのまみむめもらりるれろ"
)

# 前舌母音 {i, e} → Kiki（鋭い・速い）
_FRONT_VOWELS: frozenset = frozenset({"i", "e"})
# 後舌母音 {u, o, a} → Bouba（丸い・重い）
_BACK_VOWELS:  frozenset = frozenset({"u", "o", "a"})

# ひらがな → カタカナ 変換テーブル（kana フィールド生成用）
_HIRA_TO_KATA_MAP = {chr(c): chr(c + 0x60) for c in range(ord("ぁ"), ord("ん") + 1)}
_HIRA_TO_KATA_MAP["ゔ"] = "ヴ"
_HIRA_TO_KATA = str.maketrans(_HIRA_TO_KATA_MAP)

# ================================================
# 汎用語リスト
# 一般名詞・普通名詞としてよく使われるカタカナ語。
# これらはブランド名として固有性がなく、音韻スコアが高くても
# 差別化・記憶定着・商標登録の観点で問題があることを通知する。
# ================================================
_GENERIC_KATAKANA: frozenset = frozenset({
    # IT・テクノロジー系
    "システム", "サービス", "ソリューション", "プラットフォーム",
    "ネットワーク", "テクノロジー", "デジタル", "インターネット",
    "セキュリティ", "クラウド", "アプリケーション", "ソフトウェア",
    "データ", "アルゴリズム", "プログラム", "インフラ",
    # ビジネス・組織系
    "グループ", "コーポレーション", "コーポレート", "エンタープライズ",
    "ホールディングス", "パートナーズ", "アソシエイツ", "コンサルティング",
    "マネジメント", "マーケティング", "コミュニケーション", "インターナショナル",
    "ファイナンス", "ロジスティクス", "オペレーション", "ストラテジー",
    # 創造・メディア系
    "クリエイティブ", "デザイン", "プロダクション", "エージェンシー",
    "メディア", "コンテンツ", "プランニング", "エンターテインメント",
    # 教育・研究系
    "アカデミー", "インスティテュート", "センター", "ラボ", "ラボラトリー",
    "スクール", "カレッジ", "ユニバーシティ",
    # 一般名詞系
    "イノベーション", "トランスフォーメーション", "サポート", "サポーター",
    "プロジェクト", "プロダクト", "プロセス", "チーム", "ユニット",
    "スタジオ", "ファクトリー", "ファンド", "ベンチャー", "スタートアップ",
    "エンジニアリング", "テスト", "リサーチ", "アナリティクス",
})

# デフォルト重み
_DEFAULT_AXIS_A: Dict[str, float] = {
    "a_len": 0.35, "a_open": 0.30, "a_sp": 0.20, "a_yoon": 0.15,
}
_DEFAULT_AXIS_B: Dict[str, float] = {
    "b_rhythm": 0.50, "b_vowel": 0.50,
}
_DEFAULT_AXIS_W: Dict[str, float] = {
    "axis_a": 0.70, "axis_b": 0.30,
}


# ================================================
# 内部ユーティリティ
# ================================================

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    """非負値・合計1.0 に正規化する。"""
    nonneg = {k: max(0.0, float(v)) for k, v in w.items()}
    total = sum(nonneg.values()) or 1.0
    return {k: v / total for k, v in nonneg.items()}


# ================================================
# 軸A: 発音容易性 (Phonological Ease)
# 全て 高=発音しやすい [0, 1]
# ================================================

def a_len(
    M: int,
    mu_lo: int   = _A_LEN_MU_LO,
    mu_hi: int   = _A_LEN_MU_HI,
    sigma: float = _A_LEN_SIGMA,
) -> float:
    """
    モーラ長さ適合スコア。

    最適範囲 [mu_lo, mu_hi] で 1.0、範囲外では d=|M-最近接端| の
    ガウス減衰: exp(-d² / 2σ²)。

    旧バグ修正:
      epi_scoring_final_plane.py は ``1 - exp(-d²/2σ²)`` を使用しており
      d=0（最適モーラ数）のとき 0.0 を返していた。
      正しくは ``exp(-d²/2σ²)`` = d=0 で 1.0。
    """
    if mu_lo <= M <= mu_hi:
        return 1.0
    d = float(mu_lo - M if M < mu_lo else M - mu_hi)
    return float(math.exp(-(d * d) / (2.0 * sigma * sigma)))


def a_open(moras: List[Mora]) -> float:
    """
    開音節比率。

    vowel が None でないモーラ（母音を持つ）の割合。
    ー（長音）は直前の母音を引き継ぐため開音節扱い (vowel != None)。
    ン・ッ は vowel=None → 閉音節（ペナルティ）。
    """
    if not moras:
        return 0.0
    n_open = sum(1 for m in moras if m.vowel is not None)
    return n_open / len(moras)


def a_sp(moras: List[Mora]) -> float:
    """
    促音・撥音の難易度スコア（品質型: 高=良い）。

    ッ（促音）は完全閉鎖を強制するため重みを 1.0、
    ン（撥音）は共鳴音で比較的自然なため重みを 0.5 とする。
    ー（長音）はペナルティなし（旧実装の修正を維持）。

    設計意図:
      旧実装では ン も ッ も等しく 1.0 でペナルティしていたため
      a_open と常に同値になる問題があった（冗長）。
      重み差別化により a_open（開音節比率）と独立した指標となる。

      例:
        ホンダ  [ほ,ん,だ]    a_sp = 1 - 0.5/3 ≈ 0.833  （ン1個）
        ネット  [ね,っ,と]    a_sp = 1 - 1.0/3 ≈ 0.667  （ッ1個）
        シンブン [し,ん,ぶ,ん] a_sp = 1 - 1.0/4 = 0.750  （ン2個）
        ソニー  [そ,に,ー]    a_sp = 1.0               （ペナルティなし）
    """
    if not moras:
        return 1.0
    penalty = 0.0
    for m in moras:
        if m.surface == _SOKUON_HIRA and m.vowel is None:
            penalty += 1.0   # ッ: 完全閉鎖 → フルペナルティ
        elif m.surface == _MORAIC_N_HIRA and m.vowel is None:
            penalty += 0.5   # ン: 共鳴鼻音 → ハーフペナルティ
    return max(0.0, 1.0 - penalty / len(moras))


def a_yoon(moras: List[Mora]) -> float:
    """
    拗音の少なさ（is_yoon=True のモーラが少ないほど高い）。

    1.0 = 拗音なし（発音しやすい）
    0.0 = 全て拗音
    """
    if not moras:
        return 1.0
    n_yoon = sum(1 for m in moras if m.is_yoon)
    return 1.0 - n_yoon / len(moras)


def compute_axis_a(
    moras: List[Mora],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """軸A の加重平均スコア。weights は合計1に正規化される。"""
    w = _normalize_weights(weights or _DEFAULT_AXIS_A)
    return _clamp01(
        w.get("a_len",  0.35) * a_len(len(moras))
        + w.get("a_open", 0.30) * a_open(moras)
        + w.get("a_sp",   0.20) * a_sp(moras)
        + w.get("a_yoon", 0.15) * a_yoon(moras)
    )


# ================================================
# 軸B: 記憶容易性 (Memorability)
# 全て 高=覚えやすい [0, 1]
# ================================================

def b_rhythm(moras: List[Mora]) -> float:
    """
    リズム規則性（品質型: 高=規則的・記憶しやすい）。

    AAAA型（隣接同一母音）と ABAB型（周期2交替）の両パターンを検出し、
    より高いスコアを採用する。

    パターン定義:
      adj  = 隣接同一母音率: V[i]==V[i+1] の比率
      p2   = 周期2交替率:   V[i]==V[i+2] の比率（n>=3 のとき）

    例:
      パナマ    [a,a,a]     adj=1.0  p2=1.0 → 1.00  （AAAA型）
      グーグル   [u,u,u]     adj=1.0         → 1.00  （AAAA型）
      サクラ    [a,u,a]     adj=0.0  p2=1.0 → 1.00  （ABA型: 対称リズム）
      アディダス  [a,e,a,u]   adj=0.0  p2=0.5 → 0.50  （部分ABAB）
      メルカリ   [e,u,a,i]   adj=0.0  p2=0.0 → 0.00  （パターンなし）
    """
    V = [m.vowel for m in moras if m.vowel is not None]
    if len(V) < 2:
        return 1.0
    n = len(V)

    # パターン1: 隣接同一母音（AAAA型）
    adj_same = sum(1 for i in range(n - 1) if V[i] == V[i + 1]) / (n - 1)

    # パターン2: 周期2交替（ABAB / ABA 型）
    if n >= 3:
        period2 = sum(1 for i in range(n - 2) if V[i] == V[i + 2]) / (n - 2)
    else:
        period2 = 0.0

    return max(adj_same, period2)


def b_vowel(moras: List[Mora]) -> float:
    """
    母音調和度（前舌/後舌への偏り）。

    前舌{i,e} または 後舌{u,o,a} のどちらかに偏るほど高い。
    0.5 = 前舌・後舌が均等（最低値）

    例:
      パナマ [a,a,a]: back=3, front=0 → 3/3 = 1.00
      キキ   [i,i]:   front=2, back=0 → 2/2 = 1.00
      ソニー [o,i,i]:  front=2, back=1 → 2/3 ≈ 0.67
      メルカリ [e,u,a,i]: front=2, back=2 → 2/4 = 0.50
    """
    V = [m.vowel for m in moras if m.vowel is not None]
    if not V:
        return 0.5
    n_front = sum(1 for v in V if v in _FRONT_VOWELS)
    n_back  = sum(1 for v in V if v in _BACK_VOWELS)
    total   = n_front + n_back
    if total == 0:
        return 0.5
    return max(n_front, n_back) / total


def compute_axis_b(
    moras: List[Mora],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """軸B の加重平均スコア。"""
    w = _normalize_weights(weights or _DEFAULT_AXIS_B)
    return _clamp01(
        w.get("b_rhythm", 0.50) * b_rhythm(moras)
        + w.get("b_vowel",  0.50) * b_vowel(moras)
    )


# ================================================
# 軸C: 印象・方向性 (Brand Impression)
# 合計スコアに含めない・個別表示のみ
# ================================================

def c_strength(moras: List[Mora]) -> float:
    """
    力強さ（濁音で始まるモーラの比率）。[0, 1]

    0 = 清音のみ（軽快・クリーン）
    1 = 全て濁音（力強い・重厚）

    ※発音の難易とは無関係。ブランド印象の指標。
    """
    if not moras:
        return 0.0
    voiced = sum(
        1 for m in moras
        if m.surface and m.surface[0] in _VOICED_HIRA_INITIALS
    )
    return voiced / len(moras)


def c_sharpness(moras: List[Mora]) -> float:
    """
    鋭さ（Kiki-Bouba 音象徴効果）。[-1, +1]

    +1 = 前舌母音優位（Kiki: 鋭い・速い・小さい）
    -1 = 後舌母音優位（Bouba: 丸い・大きい・重い）
     0 = 中立

    ※C軸の個別表示のみ。合計スコアには含めない。
    """
    V = [m.vowel for m in moras if m.vowel is not None]
    if not V:
        return 0.0
    n_front = sum(1 for v in V if v in _FRONT_VOWELS)
    n_back  = sum(1 for v in V if v in _BACK_VOWELS)
    total   = n_front + n_back
    if total == 0:
        return 0.0
    return (n_front - n_back) / total


def c_fluency(moras: List[Mora]) -> float:
    """
    流暢さ（共鳴音の比率）。[0, 1]

    共鳴音 = ナ行・マ行・ラ行で始まるモーラ + ん + ー
    0 = 閉鎖音・破裂音のみ（硬い・機械的）
    1 = 全て共鳴音（滑らか・柔らかい）
    """
    if not moras:
        return 0.0
    resonant = sum(
        1 for m in moras
        if (
            not m.is_special
            and m.surface
            and m.surface[0] in _RESONANT_HIRA_INITIALS
        )
        or m.surface in {_MORAIC_N_HIRA, _CHOON}
    )
    return resonant / len(moras)


# ================================================
# 汎用語フラグ
# ================================================

def is_generic(name: str) -> bool:
    """
    名前が汎用カタカナ語リストに含まれるか判定する。

    True が返った場合: 音韻スコアが高くても、ブランド名として固有性・
    差別化・商標登録可能性が低い可能性がある。

    判定は正規化（ひらがな→カタカナ、長音・ー統一）後に行う。
    大文字小文字・全半角・濁音付き変形には対応しない（katakana exact match）。

    Returns
    -------
    bool: True = 汎用語と判定, False = 判定できない（固有名の可能性あり）
    """
    # カタカナ正規化（ひらがな入力に対応）
    normalized = to_hira(name.strip()).translate(_HIRA_TO_KATA)
    return normalized in _GENERIC_KATAKANA


# ================================================
# 設定読み込み
# ================================================

def load_phonology_weights(
    path: "str | Path" = "configs/weights.yaml",
) -> Dict:
    """
    configs/weights.yaml の phonology_weights セクションを読み込む。
    ファイルが存在しない場合は空辞書を返す（デフォルト重みが使われる）。
    """
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("phonology_weights", {})


# ================================================
# メインAPI
# ================================================

def evaluate_phonology(
    name: str,
    weights: Optional[Dict] = None,
) -> Dict:
    """
    3軸音韻評価のメインAPI。

    Parameters
    ----------
    name    : 評価対象の名前（カタカナ・ひらがな・ローマ字混在可）
    weights : phonology_weights 形式の辞書（None のとき YAML から自動読み込み）

    Returns
    -------
    dict — CLAUDE.md 出力契約
      raw=[0,1]        : a_*, b_*, axis_a, axis_b, c_strength, c_fluency
      display=[0,100]  : axis_a_display, axis_b_display
      c_sharpness は [-1, +1]（C軸個別表示のみ、合計に含めない）
      Drivers 必須キー : M, mora_str
    """
    name = (name or "").strip()
    if not name:
        return _empty_result(name)

    # テキスト正規化
    hira  = to_hira(name)
    kana  = hira.translate(_HIRA_TO_KATA)   # ひらがな→カタカナ（ー は保持）
    moras = kana_to_moras(hira)
    M     = len(moras)

    if M == 0:
        return _empty_result(name)

    # 汎用語フラグ（音韻とは独立して判定）
    generic_flag = is_generic(name)

    # 重みの解決（引数 > YAML > デフォルト）
    cfg  = weights if weights is not None else load_phonology_weights()
    w_a  = cfg.get("axis_a", _DEFAULT_AXIS_A)
    w_b  = cfg.get("axis_b", _DEFAULT_AXIS_B)
    # axis_weights は app.py / batch_eval.py 側で合成するため ここでは読み捨てる
    # （将来 evaluate_phonology 内で combined score を返す場合に使用）
    _ = cfg.get("axis_weights", _DEFAULT_AXIS_W)

    # a_len のパラメータ（YAML 上書き可）
    lp = cfg.get("a_len_params", {})
    val_a_len = a_len(
        M,
        mu_lo=int(lp.get("mu_lo", _A_LEN_MU_LO)),
        mu_hi=int(lp.get("mu_hi", _A_LEN_MU_HI)),
        sigma=float(lp.get("sigma", _A_LEN_SIGMA)),
    )

    # 軸A サブスコア
    val_a_open = a_open(moras)
    val_a_sp   = a_sp(moras)
    val_a_yoon = a_yoon(moras)

    w_a_n = _normalize_weights(w_a)
    axis_a = _clamp01(
        w_a_n.get("a_len",  0.35) * val_a_len
        + w_a_n.get("a_open", 0.30) * val_a_open
        + w_a_n.get("a_sp",   0.20) * val_a_sp
        + w_a_n.get("a_yoon", 0.15) * val_a_yoon
    )

    # 軸B サブスコア
    val_b_rhythm = b_rhythm(moras)
    val_b_vowel  = b_vowel(moras)

    w_b_n = _normalize_weights(w_b)
    axis_b = _clamp01(
        w_b_n.get("b_rhythm", 0.50) * val_b_rhythm
        + w_b_n.get("b_vowel",  0.50) * val_b_vowel
    )

    # 軸C（合計しない）
    val_c_strength  = c_strength(moras)
    val_c_sharpness = c_sharpness(moras)
    val_c_fluency   = c_fluency(moras)

    # Drivers 表示用モーラ列
    mora_str = "|".join(m.surface for m in moras)

    return {
        # --- メタ ---
        "name":     name,
        "kana":     kana,
        "hira":     hira,
        "mora_str": mora_str,
        "M":        M,
        # --- 軸A raw [0,1] ---
        "a_len":  val_a_len,
        "a_open": val_a_open,
        "a_sp":   val_a_sp,
        "a_yoon": val_a_yoon,
        "axis_a": axis_a,
        # --- 軸B raw [0,1] ---
        "b_rhythm": val_b_rhythm,
        "b_vowel":  val_b_vowel,
        "axis_b":   axis_b,
        # --- 軸C 個別表示（合計に含めない）---
        "c_strength":  val_c_strength,
        "c_sharpness": val_c_sharpness,
        "c_fluency":   val_c_fluency,
        # --- display [0,100] ---
        "axis_a_display": round(axis_a * 100),
        "axis_b_display": round(axis_b * 100),
        # --- 後方互換キー（epi.py シムが参照）---
        "EPI":    axis_a,
        "f_len":  val_a_len,
        "f_open": val_a_open,
        "f_sp":   val_a_sp,
        "f_yoon": val_a_yoon,
        "mora":   [m.surface for m in moras],
        # --- スコープ注記 ---
        "is_generic": generic_flag,  # True=汎用語の可能性（音韻スコアは参考のみ）
    }


def _empty_result(name: str) -> Dict:
    """空入力・変換結果ゼロ時のデフォルト値。"""
    return {
        "name": name, "kana": "", "hira": "", "mora_str": "", "M": 0,
        "a_len": 0.0, "a_open": 0.0, "a_sp": 1.0, "a_yoon": 1.0, "axis_a": 0.0,
        "b_rhythm": 0.0, "b_vowel": 0.5, "axis_b": 0.0,
        "c_strength": 0.0, "c_sharpness": 0.0, "c_fluency": 0.0,
        "axis_a_display": 0, "axis_b_display": 0,
        "EPI": 0.0, "f_len": 0.0, "f_open": 0.0, "f_sp": 1.0, "f_yoon": 1.0,
        "mora": [],
        "is_generic": False,
    }


# ================================================
# セルフテスト
# python -m src.features.phonology
# ================================================

if __name__ == "__main__":
    samples = [
        "コーラ", "ソニー", "トヨタ", "サクラ", "パナマ",
        "システム", "キャラメル", "シンブン", "メルカリ", "キキ",
    ]
    print(
        f"{'名前':<10} M  axis_a  axis_b  a_len  a_open  a_sp  a_yoon  "
        f"b_rhythm  b_vowel  c_str  c_sharp  c_flu"
    )
    print("-" * 90)
    for nm in samples:
        r = evaluate_phonology(nm)
        print(
            f"{nm:<10} {r['M']:2d}  "
            f"{r['axis_a']:.3f}  {r['axis_b']:.3f}  "
            f"{r['a_len']:.3f}  {r['a_open']:.3f}   {r['a_sp']:.3f}  "
            f"{r['a_yoon']:.3f}   {r['b_rhythm']:.3f}     {r['b_vowel']:.3f}   "
            f"{r['c_strength']:.3f}  {r['c_sharpness']:+.3f}   {r['c_fluency']:.3f}"
        )
