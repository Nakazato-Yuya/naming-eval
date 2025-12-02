# src/features/epi.py
# -*- coding: utf-8 -*-
"""
EPI 指標計算（長音「ー」対応・濁音/半濁音追加版）
- ポリシー:
  * f_len, f_open, f_sp, f_yoon に加えて f_voiced, f_semi_voiced を計算
  * 「ー」は母音を保持する長音として扱う
"""

from __future__ import annotations

import math
import yaml
from pathlib import Path
from typing import Dict, List

from src.features.reading import normalize_kana, to_mora

# =========================
# 設定 (weights.yaml 互換)
# =========================

def _load_weights():
    # 設定ファイルがなければ空辞書を返す安全策
    p = Path("configs/weights.yaml")
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

W = _load_weights()
LEN_SIGMA = float(W.get("final_params", {}).get("delta", 1.0))

# =========================
# 定数・文字定義
# =========================

SPECIALS_ALL = {"ン", "ッ", "ー"}
SPECIALS_NO_VOWEL = {"ン", "ッ"}

# 濁音（Voiced）：ガ行、ザ行、ダ行、バ行
VOICED_CHARS = set("ガギグゲゴザジズゼゾダヂヅデドバビブベボ")
# 半濁音（Semi-Voiced）：パ行
SEMI_VOICED_CHARS = set("パピプペポ")

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

# =========================
# 個別指標
# =========================

def f_len(mora_count: int, low: int = 2, high: int = 4) -> float:
    """長さペナルティ（0=最適, 1=悪い）"""
    if mora_count <= 0:
        return 1.0
    if low <= mora_count <= high:
        d = 0.0
    elif mora_count < low:
        d = low - mora_count
    else:
        d = mora_count - high
    sigma = max(1e-6, LEN_SIGMA)
    return _clamp01(1.0 - math.exp(-(d * d) / (2 * sigma * sigma)))

def f_open(mora_list: List[str]) -> float:
    """開音節不足（0=良い, 1=悪い）"""
    M = len(mora_list)
    if M == 0:
        return 1.0
    open_count = sum(1 for m in mora_list if m not in SPECIALS_NO_VOWEL)
    return _clamp01(1.0 - (open_count / M))

def f_sp(mora_list: List[str]) -> float:
    """特殊モーラ比（多いほどスコア1に近づく＝悪い）"""
    M = len(mora_list) or 1
    sp = sum(1 for m in mora_list if m in SPECIALS_ALL)
    return sp / M

def f_yoon(mora_list: List[str]) -> float:
    """拗音比（多いほどスコア1に近づく＝悪い）"""
    M = len(mora_list) or 1
    # 2文字以上（きゃ、しゅ等）を拗音とみなす
    return sum(1 for m in mora_list if len(m) > 1) / M

def f_voiced(kana: str) -> float:
    """
    濁音比（0=なし ～ 1=全て濁音）
    ※ 力強さの指標（EPIとしては発音負荷として扱う場合が多い）
    """
    if not kana:
        return 0.0
    v_count = sum(1 for ch in kana if ch in VOICED_CHARS)
    return v_count / len(kana)

def f_semi_voiced(kana: str) -> float:
    """
    半濁音比（0=なし ～ 1=全て半濁音）
    ※ ポップさ・破裂音の指標
    """
    if not kana:
        return 0.0
    p_count = sum(1 for ch in kana if ch in SEMI_VOICED_CHARS)
    return p_count / len(kana)

# =========================
# 合成 EPI
# =========================

def epi_weighted(mora_list: List[str], kana: str) -> float:
    """
    YAMLの重みを使って合成。
    YAMLに f_voiced, f_semi_voiced がなければ重み0として計算される。
    """
    w = W.get("epi_weights", {}) or {}
    
    # 各スコアを計算
    scores = {
        "f_len":  f_len(len(mora_list)),
        "f_open": f_open(mora_list),
        "f_sp":   f_sp(mora_list),
        "f_yoon": f_yoon(mora_list),
        "f_voiced": f_voiced(kana),
        "f_semi_voiced": f_semi_voiced(kana),
    }

    num = sum(float(w.get(k, 0.0)) * scores[k] for k in scores)
    den = sum(float(w.get(k, 0.0)) for k in scores)
    return float(num / den) if den > 0 else 0.0

# =========================
# 外部API
# =========================

def evaluate_name(name: str) -> Dict:
    kana: str = normalize_kana(name)
    mora: List[str] = to_mora(kana)
    
    # 新指標の計算
    val_voiced = f_voiced(kana)
    val_semi = f_semi_voiced(kana)
    
    return {
        "name":  str(name),
        "kana":  kana,
        "mora":  list(mora),
        "M":     len(mora),
        "f_len": f_len(len(mora)),
        "f_open":f_open(mora),
        "f_sp":  f_sp(mora),
        "f_yoon":f_yoon(mora),
        "f_voiced": val_voiced,
        "f_semi_voiced": val_semi,
        "EPI":   epi_weighted(mora, kana),
    }

def epi_from_name(name: str) -> Dict:
    return evaluate_name(name)