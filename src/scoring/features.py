# -*- coding: utf-8 -*-
"""
Japanese phonological feature extraction.

- Treat 長音記号「ー」 as:
  (1) a special mora (counts toward f_sp), and
  (2) a vowel-bearing mora for open-syllable ratio (f_open).
- Normalize Katakana→Hiragana.
- Robust mora segmentation incl. っ, ん, ー, 拗音(ゃゅょ), 長音連続(ーーー...).
- Provide a single source of truth used by both app and batch_eval.

Public API:
- extract_features(name: str) -> dict[str, float]
- evaluate_epi(feats: dict[str, float], weights: dict[str, float] | None) -> float
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Optional

# Katakana → Hiragana
KATAKANA_TO_HIRA = str.maketrans({
    **{chr(k): chr(k - 0x60) for k in range(ord('ァ'), ord('ン') + 1)},
    'ヴ': 'ゔ',
})

# Base vowel mapping (hiragana)
VOWEL_OF = {
    'あ':'a','い':'i','う':'u','え':'e','お':'o',
    'か':'a','き':'i','く':'u','け':'e','こ':'o',
    'さ':'a','し':'i','す':'u','せ':'e','そ':'o',
    'た':'a','ち':'i','つ':'u','て':'e','と':'o',
    'な':'a','に':'i','ぬ':'u','ね':'e','の':'o',
    'は':'a','ひ':'i','ふ':'u','へ':'e','ほ':'o',
    'ま':'a','み':'i','む':'u','め':'e','も':'o',
    'や':'a','ゆ':'u','よ':'o',
    'ら':'a','り':'i','る':'u','れ':'e','ろ':'o',
    'わ':'a','ゐ':'i','ゑ':'e','を':'o','ゔ':'u',
    'ぁ':'a','ぃ':'i','ぅ':'u','ぇ':'e','ぉ':'o',  # small vowels fallback
}

SOKUON = 'っ'
MORAIC_N = 'ん'
CHOON = 'ー'

@dataclass
class Mora:
    surface: str
    vowel: Optional[str]          # None for っ/ん
    is_special: bool              # True for ー/っ/ん
    is_yoon: bool                 # きゃ/しゅ等

def to_hira(s: str) -> str:
    return s.translate(KATAKANA_TO_HIRA)

# 拗音を先に、次に1文字仮名、長音/促音/撥音を拾う
MORA_RE = re.compile(
    r"(きゃ|きゅ|きょ|しゃ|しゅ|しょ|ちゃ|ちゅ|ちょ|にゃ|にゅ|にょ|ひゃ|ひゅ|ひょ|みゃ|みゅ|みょ|りゃ|りゅ|りょ|ぎゃ|ぎゅ|ぎょ|じゃ|じゅ|じょ|びゃ|びゅ|びょ|ぴゃ|ぴゅ|ぴょ)"
    r"|([ぁ-んゔ])"
    r"|(" + CHOON + r")"
    r"|(" + SOKUON + r")"
    r"|(" + MORAIC_N + r")"
)

def kana_to_moras(hira: str) -> List[Mora]:
    moras: List[Mora] = []
    last_vowel: Optional[str] = None
    for m in MORA_RE.finditer(hira):
        g = m.group(0)
        if g == CHOON:
            # 長音は直前の母音を引き継ぐ。無い場合は 'a' を採用（稀ケース）
            v = last_vowel if last_vowel is not None else 'a'
            moras.append(Mora(surface=CHOON, vowel=v, is_special=True, is_yoon=False))
            last_vowel = v
        elif g == SOKUON:
            moras.append(Mora(surface=SOKUON, vowel=None, is_special=True, is_yoon=False))
            # last_vowel は更新しない
        elif g == MORAIC_N:
            moras.append(Mora(surface=MORAIC_N, vowel=None, is_special=True, is_yoon=False))
            last_vowel = None
        else:
            # base kana or yoon cluster
            is_yoon = len(g) == 2
            base = g[0]
            v = VOWEL_OF.get(base)
            moras.append(Mora(surface=g, vowel=v, is_special=False, is_yoon=is_yoon))
            last_vowel = v
    return moras

def _safe_ratio(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0

def extract_features(name: str) -> Dict[str, float]:
    hira = to_hira(name)
    moras = kana_to_moras(hira)
    n = len(moras)

    n_special = sum(1 for m in moras if m.is_special)     # ー/っ/ん
    n_yoon = sum(1 for m in moras if m.is_yoon)
    n_open = sum(1 for m in moras if m.vowel is not None) # 母音を持つモーラ

    feats = {
        'f_len': float(n),
        'f_sp': _safe_ratio(n_special, n),
        'f_yoon': _safe_ratio(n_yoon, n),
        'f_open': _safe_ratio(n_open, n),
    }
    return feats

# デフォルト重み（暫定）
DEFAULT_WEIGHTS = {
    'f_len': -0.10,   # 長いほどやや難
    'f_open': +0.50,  # 開音節が多いほど易
    'f_sp': -0.25,    # 特殊モーラが多いほどやや難
    'f_yoon': -0.10,  # 拗音比が高いとやや難
}

def evaluate_epi(feats: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    s = sum(w.get(k, 0.0) * v for k, v in feats.items())
    # 0..1 へソフトに潰す
    epi = 1.0 / (1.0 + pow(2.71828, -s))
    return float(epi)
