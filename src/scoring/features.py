# -*- coding: utf-8 -*-
"""
Japanese phonological feature extraction (完成版).

・長音「ー」を 1) 特殊モーラ として数える（f_spに効く）
　　　　　     2) 母音を持つ開音モーラとして扱う（f_openに効く）
・ひらがな/カタカナ混在を正規化（NFKC → ひらがな主体）
・モーラ分割：拗音(ゃゅょ)、小書き母音(ぁぃぅぇぉ/ゎ)、促音(っ)、撥音(ん)、長音(ー)
・UI/CLIの両方から同じ関数を呼べる「単一の真実のソース」

Public API:
- extract_features(name: str) -> dict[str, float]   # 0..1向きに整えた特徴
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

# ----------------------------
# 文字正規化
# ----------------------------
# カタカナ→ひらがな（U+30A1..U+30F3）
KATA_TO_HIRA = {chr(k): chr(k - 0x60) for k in range(ord("ァ"), ord("ン") + 1)}
KATAKANA_TO_HIRA = str.maketrans({**KATA_TO_HIRA, "ヴ": "ゔ"})

CHOON = "ー"   # 長音
SOKUON = "っ"  # 促音
MORAIC_N = "ん"  # 撥音

# ひらがなの最終母音（ベース音）
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
    "わ": "a", "ゐ": "i", "ゑ": "e", "を": "o", "ゔ": "u",
    # 小書き母音（フォールバック）
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
}

SMALL_VOWELS = set("ゃゅょぁぃぅぇぉゎ")
SPECIAL_MORA = {CHOON, SOKUON, MORAIC_N}

def to_hira(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    # カタカナ→ひらがな（長音「ー」はそのまま残る＝U+30FC）
    s = s.translate(KATAKANA_TO_HIRA)
    # ひらがな + 長音 だけ残す（英数・記号を落とす）
    s = re.sub(rf"[^\u3040-\u309F{CHOON}]", "", s)
    return s

# ----------------------------
# モーラ表現
# ----------------------------
@dataclass
class Mora:
    surface: str               # 表記
    vowel: Optional[str]       # 母音（っ/んはNone、ーは直前の母音を継承）
    is_special: bool           # ー/っ/ん
    is_yoon: bool              # きゃ/しゅ/ふぁ等（小書き母音と結合）

def kana_to_moras(hira: str) -> List[Mora]:
    """ひらがな列→モーラ列。小書き母音も一般化して結合。"""
    moras: List[Mora] = []
    last_vowel: Optional[str] = None
    i = 0
    while i < len(hira):
        ch = hira[i]

        # 特殊モーラ
        if ch == CHOON:
            v = last_vowel if last_vowel is not None else "a"  # 稀に先頭長音を保険
            moras.append(Mora(surface=CHOON, vowel=v, is_special=True, is_yoon=False))
            # last_vowel は同じ（母音延長）
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

        # ベース仮名 + （あれば）小書き母音を結合 → 拗音/二重母音系を 1 モーラに
        if i + 1 < len(hira) and hira[i + 1] in SMALL_VOWELS:
            cluster = hira[i : i + 2]  # 例) きゃ / ふぉ / くゎ
            base = hira[i]
            v = VOWEL_OF.get(base, None)
            moras.append(Mora(surface=cluster, vowel=v, is_special=False, is_yoon=True))
            last_vowel = v
            i += 2
        else:
            base = ch
            v = VOWEL_OF.get(base, None)
            moras.append(Mora(surface=base, vowel=v, is_special=False, is_yoon=False))
            last_vowel = v
            i += 1

    return moras

def _safe_ratio(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0

# ----------------------------
# 特徴量（0..1 向きに統一）
# ----------------------------
def _f_len_from_M(M: int, min_ok: int = 2, max_ok: int = 9) -> float:
    """
    長さペナルティを 0..1 に正規化（短いほど1）。
    min_ok=2 で 2モーラを理想上限(=1.0)、max_ok=9 で 9モーラを下限(=0.0)に線形補間。
    """
    if M <= min_ok:
        return 1.0
    if M >= max_ok:
        return 0.0
    return 1.0 - (M - min_ok) / (max_ok - min_ok)

def extract_features(name: str) -> Dict[str, float]:
    """入力名 → 0..1 特徴量（f_len, f_open, f_sp, f_yoon）とモーラ情報を返す。"""
    hira = to_hira(name)
    moras = kana_to_moras(hira)
    M = len(moras)

    n_special = sum(1 for m in moras if m.is_special)        # ー/っ/ん
    n_yoon = sum(1 for m in moras if m.is_yoon)              # きゃ/ふぁ 等
    n_open  = sum(1 for m in moras if m.vowel is not None)   # 母音を持つモーラ（ー含む）

    ratio_sp = _safe_ratio(n_special, M)                     # 多いほど難
    ratio_y  = _safe_ratio(n_yoon, M)                        # 多いほど難
    ratio_op = _safe_ratio(n_open, M)                        # 多いほど易

    feats = {
        # すべて「1=言いやすい」向きに統一
        "f_len":  _f_len_from_M(M),      # 短いほど1
        "f_open": ratio_op,              # 開音比が高いほど1
        "f_sp":   1.0 - ratio_sp,        # 特殊モーラが少ないほど1
        "f_yoon": 1.0 - ratio_y,         # 拗音が少ないほど1
        # 参考表示用
        "_M": float(M),
        "_mora_str": "|".join(m.surface for m in moras),
    }
    return feats

# ----------------------------
# EPI 合成（和 or 幾何平均）
# ----------------------------
DEFAULT_WEIGHTS = {
    "f_len":  0.18,
    "f_open": 0.16,
    "f_sp":   0.16,
    "f_yoon": 0.12,
}  # 残りは UI/設定で正規化される前提でも可

def _normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    # 非負で合計1に（負は0に潰す）
    nonneg = {k: max(0.0, float(v)) for k, v in w.items()}
    s = sum(nonneg.values()) or 1.0
    return {k: v / s for k, v in nonneg.items()}

def evaluate_epi(
    feats: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
    mode: str = "sum",  # "sum"（加重平均） or "geo"（加重幾何平均＝積）
) -> float:
    """
    mode="sum":  EPI = Σ w_i f_i
    mode="geo":  EPI = Π f_i^{w_i}  （= exp(Σ w_i log f_i)）
    いずれも 0..1 に収まる。
    """
    keys = ["f_len", "f_open", "f_sp", "f_yoon"]
    f = {k: float(max(0.0, min(1.0, feats.get(k, 0.0)))) for k in keys}
    w = _normalize_weights(weights or DEFAULT_WEIGHTS)

    if mode == "geo":
        # 幾何平均：ボトルネック（どれかが低い）を強調
        s = 0.0
        for k in keys:
            x = max(1e-12, f[k])  # 数値安定化
            s += w[k] * math.log(x)
        epi = math.exp(s)
    else:
        # 加重平均：バランス型
        epi = sum(w[k] * f[k] for k in keys)

    # 安全に 0..1 クリップ
    return float(max(0.0, min(1.0, epi)))


# ----------------------------
# 簡単セルフテスト（必要ならコメントアウト）
# ----------------------------
if __name__ == "__main__":
    for name in ["コーラ", "コーーラ", "アーラ", "キャラメル", "ラーメン", "カップヌードル"]:
        feats = extract_features(name)
        epi_sum = evaluate_epi(feats, mode="sum")
        epi_geo = evaluate_epi(feats, mode="geo")
        print(
            f"{name}\tM={int(feats['_M'])}\t[{feats['_mora_str']}]  "
            f"f_len={feats['f_len']:.2f}  f_open={feats['f_open']:.2f}  "
            f"f_sp={feats['f_sp']:.2f}  f_yoon={feats['f_yoon']:.2f}  "
            f"EPI(sum)={epi_sum:.3f}  EPI(geo)={epi_geo:.3f}"
        )
