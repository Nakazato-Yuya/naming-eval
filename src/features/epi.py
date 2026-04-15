# src/features/epi.py
# -*- coding: utf-8 -*-
"""
後方互換シム: phonology.py に処理を委譲しつつ、既存の公開 API を維持する。

変更点（旧実装からの差異）:
  - f_len / f_open / f_sp / f_yoon のスコア方向を統一
      旧: ペナルティ型（0=最良, 高=悪い）
      新: 品質型（1=最良, 高=良い） ← phonology.py 準拠
  - f_sp から長音「ー」を除外（旧実装では不当ペナルティ）
  - f_voiced は EPI の合成から除外（印象軸 C-1 相当のため）
  - epi_weighted() の kana 引数をオプション化（テスト失敗修正）

維持する公開 API:
  evaluate_name(name: str) -> dict
  epi_from_name(name: str) -> dict
  epi_weighted(mora_list, kana=None) -> float
  normalize_kana(name: str) -> str
  to_mora(kana: str) -> list
  f_len, f_open, f_sp, f_yoon, f_voiced, f_semi_voiced
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

# phonology.py に委譲
from src.features.phonology import (
    evaluate_phonology,
    a_len as _a_len,
    a_open as _a_open,
    a_sp as _a_sp,
    a_yoon as _a_yoon,
    c_strength as _c_strength,
)
from src.scoring.features import kana_to_moras, to_hira

# reading.py の公開 API を再エクスポート（後方互換: test_epi_weight.py 等が参照）
from src.features.reading import normalize_kana, to_mora  # noqa: F401


# ================================================
# 後方互換: 個別指標関数
# （スコア方向は phonology.py に統一: 高=良い）
# ================================================

def f_len(mora_count: int, low: int = 2, high: int = 4) -> float:
    """長さペナルティ → 品質型に変更（phonology.a_len に委譲）。"""
    return _a_len(mora_count, mu_lo=low, mu_hi=high)


def f_open(mora_list: List[str]) -> float:
    """
    開音節比率（品質型: 高=良い）。
    mora_list はカタカナ文字列のリスト（reading.to_mora の戻り値形式）。
    """
    # カタカナ mora_list → ひらがな → Mora オブジェクト化
    hira = "".join(to_hira(m) for m in mora_list)
    moras = kana_to_moras(hira)
    return _a_open(moras)


def f_sp(mora_list: List[str]) -> float:
    """特殊閉音節モーラ少なさ（品質型: 高=良い、ー除外）。"""
    hira = "".join(to_hira(m) for m in mora_list)
    moras = kana_to_moras(hira)
    return _a_sp(moras)


def f_yoon(mora_list: List[str]) -> float:
    """拗音少なさ（品質型: 高=良い）。"""
    hira = "".join(to_hira(m) for m in mora_list)
    moras = kana_to_moras(hira)
    return _a_yoon(moras)


def f_voiced(kana: str) -> float:
    """
    濁音比率（印象軸 C-1 相当）。
    ※ EPI 合成には含めない。戻り値は後方互換のため残す。
    """
    hira = to_hira(kana)
    moras = kana_to_moras(hira)
    return _c_strength(moras)


def f_semi_voiced(kana: str) -> float:
    """
    半濁音比率（パ行）。
    ※ 後方互換のため関数は残すが EPI 合成には含めない。
    """
    SEMI_VOICED_HIRA = frozenset("ぱぴぷぺぽ")
    hira = to_hira(kana)
    if not hira:
        return 0.0
    return sum(1 for ch in hira if ch in SEMI_VOICED_HIRA) / len(hira)


# ================================================
# epi_weighted（後方互換シム）
# ================================================

def _load_epi_weights() -> Dict[str, float]:
    """configs/weights.yaml の epi_weights セクションを読み込む。"""
    p = Path("configs/weights.yaml")
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("epi_weights", {})


def epi_weighted(
    mora_list: List[str],
    kana: Optional[str] = None,   # ← オプション化（旧テスト失敗修正）
) -> float:
    """
    加重平均 EPI（後方互換）。

    内部は phonology.evaluate_phonology に委譲。
    mora_list からひらがな列を再構成して軸A スコアを計算する。
    kana 引数は後方互換のために受け取るが使用しない。
    """
    # mora_list（カタカナ）→ 文字列再結合 → phonology に渡す
    combined = "".join(mora_list)
    r = evaluate_phonology(combined)
    return r["axis_a"]


# ================================================
# evaluate_name / epi_from_name（後方互換シム）
# ================================================

def evaluate_name(name: str) -> Dict:
    """
    名前 → 評価結果辞書（後方互換キーを含む）。

    後方互換キー: name, kana, mora, M, EPI, f_len, f_open, f_sp, f_yoon,
                  f_voiced, f_semi_voiced
    新キー: axis_a, axis_b, a_*, b_*, c_*, mora_str, hira
    """
    r = evaluate_phonology(name)
    # f_voiced / f_semi_voiced は印象軸だが後方互換のため追加
    r["f_voiced"]      = r.get("c_strength", 0.0)
    r["f_semi_voiced"] = f_semi_voiced(name)
    return r


def epi_from_name(name: str) -> Dict:
    """evaluate_name のエイリアス（後方互換）。"""
    return evaluate_name(name)
