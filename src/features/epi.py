# -*- coding: utf-8 -*-
"""
EPI 指標計算（長音「ー」対応版）
- ポリシー:
  * 「ン」「ッ」「ー」を特殊モーラとして f_sp にカウントする
  * ただし「ー」は母音を保持する長音なので f_open（開音節不足ペナルティ）では
    “開音節として数える”（= ペナルティを増やさない）
- normalize_kana / to_mora は既存の reading モジュールを使用（モーラ列に「ー」を含む前提）
- EPI は 0=良い ～ 1=悪い の尺度
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
    with open(Path("configs/weights.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

W = _load_weights()
LEN_SIGMA = float(W.get("final_params", {}).get("delta", 1.0))

# =========================
# ユーティリティ
# =========================

# 特殊モーラ集合（カタカナ前提）
SPECIALS_ALL = {"ン", "ッ", "ー"}   # f_sp ではすべてカウント
SPECIALS_NO_VOWEL = {"ン", "ッ"}   # f_open では“開”に含めない（※「ー」は含めない）

def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

# =========================
# 個別指標
# =========================

def f_len(mora_count: int, low: int = 2, high: int = 4) -> float:
    """
    長さペナルティ（0=最適帯, 1=悪い）
    目標帯 low..high からの距離をガウスで潰して 0..1 に収める
    """
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
    """
    開音節“不足”ペナルティ（0=開が多い/良い, 1=不足/悪い）
    - 「ン」「ッ」は開として数えない
    - 「ー」は“開として数える”（長音は母音を保持）
    """
    M = len(mora_list)
    if M == 0:
        return 1.0
    open_count = sum(1 for m in mora_list if m not in SPECIALS_NO_VOWEL)
    open_ratio = open_count / M
    return _clamp01(1.0 - open_ratio)

def f_sp(mora_list: List[str]) -> float:
    """
    特殊モーラ比（0..1）
    - 「ン」「ッ」「ー」をカウント対象
    """
    M = len(mora_list) or 1
    sp = sum(1 for m in mora_list if m in SPECIALS_ALL)
    return sp / M

def f_yoon(mora_list: List[str]) -> float:
    """
    拗音比（0..1）
    MVP定義：1文字でないモーラ（例: 「キャ」「シュ」など）を拗音とみなす
    """
    M = len(mora_list) or 1
    return sum(1 for m in mora_list if len(m) > 1) / M

# =========================
# 合成 EPI（重みは YAML から）
# =========================

def epi_weighted(mora_list: List[str]) -> float:
    """
    EPI 合成（0=良い ～ 1=悪い）
    configs/weights.yaml の epi_weights のキーのみ合成
    """
    w = W.get("epi_weights", {}) or {}
    parts = {
        "f_len":  f_len(len(mora_list)),
        "f_open": f_open(mora_list),
        "f_sp":   f_sp(mora_list),
        "f_yoon": f_yoon(mora_list),
    }
    num = sum(float(w.get(k, 0.0)) * parts[k] for k in parts)
    den = sum(float(w.get(k, 0.0)) for k in parts)
    return float(num / den) if den > 0 else 0.0

# =========================
# 外部API
# =========================

def evaluate_name(name: str) -> Dict:
    """
    文字列から正規化→モーラ分割→各指標→合成EPI
    返却:
      - name, kana, mora(list[str]), M
      - f_len, f_open, f_sp, f_yoon
      - EPI (0..1)
    """
    kana: str = normalize_kana(name)          # 例: "コーーラ"
    mora: List[str] = to_mora(kana)           # 例: ["コ", "ー", "ー", "ラ"] を想定
    return {
        "name":  str(name),
        "kana":  kana,
        "mora":  list(mora),
        "M":     len(mora),
        "f_len": f_len(len(mora)),
        "f_open":f_open(mora),
        "f_sp":  f_sp(mora),
        "f_yoon":f_yoon(mora),
        "EPI":   epi_weighted(mora),
    }

# 旧API互換
def epi_from_name(name: str) -> Dict:
    return evaluate_name(name)
