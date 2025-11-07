# -*- coding: utf-8 -*-
"""
Japanese phonological feature extraction (完成版).

・長音「ー」を 1) 特殊モーラ として数える（f_spに効く）
　　　　　     2) 母音を持つ開音モーラとして扱う（f_openに効く）
・ひらがな/カタカナ混在を正規化（NFKC → ひらがな主体）
・モーラ分割：拗音(ゃゅょ)、小書き母音(ぁぃぅぇぉ/ゎ)、促音(っ)、撥音(ん)、長音(ー)
・濁音/半濁音は NFD 分解でベースかなに落として母音を取得（例：ぱ→は→a）
・UI/CLI の両方から同じ関数を呼べる「単一の真実のソース」

Public API
----------
- extract_features(name: str) -> dict[str, float]   # 0..1 向きの特徴
- evaluate_epi(feats: dict[str, float],
               weights: dict[str, float] | None = None,
               mode: str = "sum") -> float          # "sum" or "geo"
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional

# =========================
# 文字正規化
# =========================
# カタカナ → ひらがな（U+30A1..U+30F3）
KATA_TO_HIRA = {chr(k): chr(k - 0x60) for k in range(ord("ァ"), ord("ン") + 1)}
KATAKANA_TO_HIRA = str.maketrans({**KATA_TO_HIRA, "ヴ": "ゔ"})

CHOON = "ー"     # 長音
SOKUON = "っ"    # 促音
MORAIC_N = "ん"  # 撥音

# ひらがなのベース母音
VOWEL_OF: Dict[str, str] = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "a", "き": "i", "く": "u", "け": "e", "こ": "o",
    "さ": "a", "し": "i", "す": "u", "せ": "e", "そ": "o",
    "た": "a", "ち": "i", "つ": "u", "て": "e", "と": "o",
    "な": "a", "に": "i", "ぬ": "u", "ね": "e", "の": "o",
    "は": "a", "ひ": "i", "ふ": "u", "へ": "e", "ほ": "o",
    "ま": "a", "み": "i", "む": "u", "め": "e", "も": "o",
    "や": "a", "ゆ": "u", "よ": "o",
    "ら": "a", "り": "i", "る": "u", "れ": "e", "ろ": "o",
    "わ": "a", "ゐ": "i", "ゑ": "e", "を": "o",
    "ゔ": "u",  # 濁点付きの「う」
    # 小書き母音（フォールバック）
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
}

SMALL_VOWELS = set("ゃゅょぁぃぅぇぉゎ")
SPECIAL_MORA = {CHOON, SOKUON, MORAIC_N}


def to_hira(s: str) -> str:
    """NFKC→カタカナをひらがなへ→ひらがな＋長音以外を除去。"""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(KATAKANA_TO_HIRA)  # 長音「ー」はそのまま（U+30FC）
    s = re.sub(rf"[^\u3040-\u309F{CHOON}]", "", s)  # ひらがなと長音のみ
    return s


def base_hira_without_diacritics(ch: str) -> str:
    """
    NFD 分解で濁点/半濁点を外し、ベースのひらがなを返す。
    例: 「ぱ」→「は」, 「が」→「か」
    """
    decomp = unicodedata.normalize("NFD", ch)
    for c in decomp:
        # ひらがな帯 (ぁ..ゖ) と ゔ を優先して返す
        if "ぁ" <= c <= "ゖ" or c == "ゔ":
            return c
    return ch


# =========================
# モーラ表現
# =========================
@dataclass
class Mora:
    surface: str             # 表記
    vowel: Optional[str]     # 母音（っ/んは None、ー は直前の母音）
    is_special: bool         # ー/っ/ん
    is_yoon: bool            # 小書き母音との結合（きゃ/ふぁ 等）


def kana_to_moras(hira: str) -> List[Mora]:
    """ひらがな列 → モーラ列。小書き母音も一般化して 1 モーラ化。"""
    moras: List[Mora] = []
    last_vowel: Optional[str] = None
    i = 0
    while i < len(hira):
        ch = hira[i]

        # --- 特殊モーラ ---
        if ch == CHOON:
            v = last_vowel if last_vowel is not None else "a"  # 先頭長音の保険
            moras.append(Mora(surface=CHOON, vowel=v, is_special=True, is_yoon=False))
            # 長音は母音継続なので last_vowel は据え置き
            i += 1
            continue
        if ch == SOKUON:
            moras.append(Mora(surface=SOKUON, vowel=None, is_special=True, is_yoon=False))
            i += 1
            continue
        if ch == MORAIC_N:
            moras.append(Mora(surface=MORAIC_N, vowel=None, is_special=True, is_yoon=False))
            last_vowel = None
            i += 1
            continue

        # --- 通常モーラ（拗音を結合） ---
        if i + 1 < len(hira) and hira[i + 1] in SMALL_VOWELS:
            cluster = hira[i : i + 2]             # 例) きゃ / ふぁ / くゎ
            base0 = base_hira_without_diacritics(hira[i])
            v = VOWEL_OF.get(base0)
            moras.append(Mora(surface=cluster, vowel=v, is_special=False, is_yoon=True))
            last_vowel = v
            i += 2
        else:
            base0 = base_hira_without_diacritics(ch)
            v = VOWEL_OF.get(base0)
            moras.append(Mora(surface=ch, vowel=v, is_special=False, is_yoon=False))
            last_vowel = v
            i += 1

    return moras


def _safe_ratio(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


# =========================
# 特徴量（0..1 向きに統一）
# =========================
def _f_len_from_M(M: int, min_ok: int = 2, max_ok: int = 9) -> float:
    """
    長さペナルティを 0..1 に正規化（短いほど 1）。
    min_ok=2 を理想（=1.0）、max_ok=9 を下限（=0.0）に線形補間。
    """
    if M <= min_ok:
        return 1.0
    if M >= max_ok:
        return 0.0
    return 1.0 - (M - min_ok) / (max_ok - min_ok)


def extract_features(name: str) -> Dict[str, float]:
    """
    入力名 → 0..1 特徴量（f_len, f_open, f_sp, f_yoon）と参考表示値を返す。
    f_open: 母音を持つモーラ比（長音も母音ありとみなす）
    f_sp  : 特殊モーラ（ー/っ/ん）が少ないほど高い
    f_yoon: 拗音が少ないほど高い
    """
    hira = to_hira(name)
    moras = kana_to_moras(hira)
    M = len(moras)

    n_special = sum(1 for m in moras if m.is_special)       # ー/っ/ん
    n_yoon = sum(1 for m in moras if m.is_yoon)             # きゃ/ふぁ 等
    n_open = sum(1 for m in moras if m.vowel is not None)   # 長音含む

    ratio_sp = _safe_ratio(n_special, M)                    # 多いほど難
    ratio_y = _safe_ratio(n_yoon, M)                        # 多いほど難
    ratio_op = _safe_ratio(n_open, M)                       # 多いほど易

    feats = {
        "f_len": _f_len_from_M(M),              # 短いほど 1
        "f_open": ratio_op,                     # 開音比が高いほど 1
        "f_sp": 1.0 - ratio_sp,                 # 特殊モーラが少ないほど 1
        "f_yoon": 1.0 - ratio_y,                # 拗音が少ないほど 1
        # 参考表示
        "_M": float(M),
        "_mora_str": "|".join(m.surface for m in moras),
    }
    return feats


# =========================
# EPI 合成（和 or 幾何平均）
# =========================
DEFAULT_WEIGHTS = {
    "f_len": 0.18,
    "f_open": 0.16,
    "f_sp": 0.16,
    "f_yoon": 0.12,
}  # 残りは UI/設定側で正規化されても可


def _normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    # 非負・合計 1 に正規化（負は 0 に潰す）
    nonneg = {k: max(0.0, float(v)) for k, v in w.items()}
    s = sum(nonneg.values()) or 1.0
    return {k: v / s for k, v in nonneg.items()}


def evaluate_epi(
    feats: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
    mode: str = "sum",  # "sum":加重平均, "geo":加重幾何平均=積
) -> float:
    """
    mode="sum":  EPI = Σ w_i f_i                （バランス重視）
    mode="geo":  EPI = Π f_i^{w_i} = exp(Σ w_i log f_i)  （ボトルネック強調）
    いずれも 0..1 に収まるよう非負重み（合計 1）で合成する。
    """
    keys = ["f_len", "f_open", "f_sp", "f_yoon"]
    f = {k: float(max(0.0, min(1.0, feats.get(k, 0.0)))) for k in keys}
    w = _normalize_weights(weights or DEFAULT_WEIGHTS)

    if mode == "geo":
        # 幾何平均（どれかが極端に低いと全体も下がる）
        s = 0.0
        for k in keys:
            x = max(1e-12, f[k])  # 数値安定化
            s += w[k] * math.log(x)
        epi = math.exp(s)
    else:
        # 加重平均（和）
        epi = sum(w[k] * f[k] for k in keys)

    return float(max(0.0, min(1.0, epi)))


# =========================
# 簡単セルフテスト
# =========================
if __name__ == "__main__":
    samples = ["コーラ", "コーーラ", "アーラ", "パナマ", "ガム", "カップ", "サン", "キャラメル", "ラーメン"]
    for name in samples:
        feats = extract_features(name)
        epi_sum = evaluate_epi(feats, mode="sum")
        epi_geo = evaluate_epi(feats, mode="geo")
        print(
            f"{name}\tM={int(feats['_M'])}\t[{feats['_mora_str']}]  "
            f"f_len={feats['f_len']:.2f}  f_open={feats['f_open']:.2f}  "
            f"f_sp={feats['f_sp']:.2f}  f_yoon={feats['f_yoon']:.2f}  "
            f"EPI(sum)={epi_sum:.3f}  EPI(geo)={epi_geo:.3f}"
        )
