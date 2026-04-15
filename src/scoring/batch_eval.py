# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Dict, List

import pandas as pd

from src.features.phonology import evaluate_phonology

# =========================
# UI/CLI 共通：重みと評価関数
# =========================

@dataclass
class Weights:
    # 軸A (発音容易性)
    a_len:  float = 0.35
    a_open: float = 0.30
    a_sp:   float = 0.20
    a_yoon: float = 0.15
    # 軸B (記憶容易性)
    b_rhythm: float = 0.50
    b_vowel:  float = 0.50
    # 軸間比率
    axis_a_weight: float = 0.70
    axis_b_weight: float = 0.30

    # 旧フィールドのエイリアス (後方互換: CLI --w-len 等)
    @classmethod
    def from_legacy(
        cls,
        w_len: float = 0.35,
        w_open: float = 0.30,
        w_sp: float = 0.20,
        w_yoon: float = 0.25,
    ) -> "Weights":
        return cls(a_len=w_len, a_open=w_open, a_sp=w_sp, a_yoon=w_yoon)


def _ensure_features(row: Dict[str, object]) -> Dict[str, object]:
    """
    row の name から evaluate_phonology を呼んで全指標を返す。
    既に a_* / b_* が揃っている場合はそれを優先する。
    """
    # 新キーが揃っていればそのまま採用
    new_keys = ("a_len", "a_open", "a_sp", "a_yoon", "axis_a", "b_rhythm", "b_vowel", "axis_b")
    if all(k in row for k in new_keys):
        return dict(row)

    name = str(row.get("name", "") or "").strip()
    if not name:
        return {
            "name": "", "kana": "", "hira": "", "mora_str": "", "M": 0, "mora": [],
            "a_len": 0.0, "a_open": 0.0, "a_sp": 1.0, "a_yoon": 1.0, "axis_a": 0.0,
            "b_rhythm": 0.0, "b_vowel": 0.0, "axis_b": 0.0,
            "c_strength": 0.0, "c_sharpness": 0.0, "c_fluency": 0.0,
            "EPI": 0.0, "f_len": 0.0, "f_open": 0.0, "f_sp": 1.0, "f_yoon": 1.0,
            "axis_a_display": 0, "axis_b_display": 0,
        }

    return evaluate_phonology(name)


def _score_from_features(feat: Dict[str, object], w: Weights) -> Dict[str, float]:
    """指標と重みから axis_a / axis_b / FinalScore を計算して返す。"""
    # 軸A: 加重平均（重み合計で正規化）
    sum_a = w.a_len + w.a_open + w.a_sp + w.a_yoon
    if sum_a > 0:
        axis_a = (
            w.a_len  * float(feat.get("a_len",  0.0))
            + w.a_open * float(feat.get("a_open", 0.0))
            + w.a_sp   * float(feat.get("a_sp",   0.0))
            + w.a_yoon * float(feat.get("a_yoon", 0.0))
        ) / sum_a
    else:
        axis_a = float(feat.get("axis_a", 0.0))

    # 軸B: 加重平均
    sum_b = w.b_rhythm + w.b_vowel
    if sum_b > 0:
        axis_b = (
            w.b_rhythm * float(feat.get("b_rhythm", 0.0))
            + w.b_vowel  * float(feat.get("b_vowel",  0.0))
        ) / sum_b
    else:
        axis_b = float(feat.get("axis_b", 0.0))

    # 軸間合成
    sum_axes = w.axis_a_weight + w.axis_b_weight
    if sum_axes > 0:
        final = (w.axis_a_weight * axis_a + w.axis_b_weight * axis_b) / sum_axes
    else:
        final = axis_a

    return {
        "axis_a": axis_a,
        "axis_b": axis_b,
        "FinalScore": final,
        "EPI": axis_a,  # 後方互換
        "axis_a_display": int(round(axis_a * 100)),
        "axis_b_display": int(round(axis_b * 100)),
    }


def evaluate_df(df: pd.DataFrame, w: Weights) -> pd.DataFrame:
    """
    DataFrame → DataFrame の評価（UI/ノートブック/CLIの共有部）。
    name 列があれば evaluate_phonology で全指標を計算する。
    """
    records = df.to_dict(orient="records")
    out_rows: List[Dict[str, object]] = []

    for r in records:
        feat = _ensure_features(r)
        sc = _score_from_features(feat, w)
        row = {**r, **feat, **sc}
        out_rows.append(row)

    return pd.DataFrame(out_rows)


def evaluate_names_to_df(names: List[str], w: Weights) -> pd.DataFrame:
    """UI で名前だけのリストを渡したいときのヘルパー。"""
    base = [{"name": (n or "").strip()} for n in names if (n or "").strip()]
    return evaluate_df(pd.DataFrame(base), w)


# =========================
# CSV 書式 I/O
# =========================

_CSV_COLS = [
    "name", "axis_a", "axis_b",
    "a_len", "a_open", "a_sp", "a_yoon",
    "b_rhythm", "b_vowel",
    "c_strength", "c_sharpness", "c_fluency",
    "M", "mora_str",
    # 後方互換
    "EPI", "FinalScore",
]


def _to_csv(df_out: pd.DataFrame, out_path: Path) -> None:
    """evaluate_df の結果を CSV で書き出す。"""
    df = df_out.copy()

    # mora が list の場合は '|' 連結
    if "mora" in df.columns and "mora_str" not in df.columns:
        df["mora_str"] = df["mora"].apply(
            lambda x: "|".join(x) if isinstance(x, (list, tuple)) else str(x or "")
        )

    for c in _CSV_COLS:
        if c not in df.columns:
            df[c] = ""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df[_CSV_COLS].to_csv(out_path, index=False, encoding="utf-8")


# 旧名エイリアス（後方互換）
_to_legacy_csv = _to_csv


# 旧 API（後方互換）
def eval_rows(names: Iterable[str]) -> Iterable[Dict[str, str]]:
    """name のリストを受け取り、指標を辞書で yield（後方互換）。"""
    for name in names:
        name = (name or "").strip()
        if not name:
            continue
        r = evaluate_phonology(name)
        yield {
            "name":   r["name"],
            "EPI":    str(r.get("EPI",    0.0)),
            "f_len":  str(r.get("f_len",  0.0)),
            "f_open": str(r.get("f_open", 0.0)),
            "f_sp":   str(r.get("f_sp",   0.0)),
            "f_yoon": str(r.get("f_yoon", 0.0)),
            "M":      str(r.get("M",      0)),
            "mora":   "|".join(r.get("mora", [])),
        }


def main(
    input_csv: str = "data/processed/sample_names.csv",
    output_csv: str = "reports/sample_eval.csv",
    # 軸A重み
    a_len:  float = 0.35,
    a_open: float = 0.30,
    a_sp:   float = 0.20,
    a_yoon: float = 0.15,
    # 軸B重み
    b_rhythm: float = 0.50,
    b_vowel:  float = 0.50,
    # 軸間比率
    axis_a_weight: float = 0.70,
    axis_b_weight: float = 0.30,
    sort_by: str = "axis_a",
) -> None:
    """CSVを読み込んで evaluate_df(Weights) で採点し、CSVを書き出す。"""
    in_path  = Path(input_csv)
    out_path = Path(output_csv)

    df_in = pd.read_csv(in_path, encoding="utf-8")

    w = Weights(
        a_len=a_len, a_open=a_open, a_sp=a_sp, a_yoon=a_yoon,
        b_rhythm=b_rhythm, b_vowel=b_vowel,
        axis_a_weight=axis_a_weight, axis_b_weight=axis_b_weight,
    )
    df_eval = evaluate_df(df_in, w)

    if sort_by and sort_by in df_eval.columns:
        df_eval = df_eval.sort_values(sort_by, ascending=False).reset_index(drop=True)

    _to_csv(df_eval, out_path)
    print(f"評価結果を {out_path} に保存しました。")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Batch evaluate phonology from a CSV with a 'name' column."
    )
    p.add_argument("input",  nargs="?", default="data/processed/sample_names.csv")
    p.add_argument("output", nargs="?", default="reports/sample_eval.csv")

    # 軸A
    p.add_argument("--a-len",  dest="a_len",  type=float, default=0.35, help="a_len の重み")
    p.add_argument("--a-open", dest="a_open", type=float, default=0.30, help="a_open の重み")
    p.add_argument("--a-sp",   dest="a_sp",   type=float, default=0.20, help="a_sp の重み")
    p.add_argument("--a-yoon", dest="a_yoon", type=float, default=0.15, help="a_yoon の重み")
    # 旧エイリアス
    p.add_argument("--w-len",  dest="a_len",  type=float, help=argparse.SUPPRESS)
    p.add_argument("--w-open", dest="a_open", type=float, help=argparse.SUPPRESS)
    p.add_argument("--w-sp",   dest="a_sp",   type=float, help=argparse.SUPPRESS)
    p.add_argument("--w-yoon", dest="a_yoon", type=float, help=argparse.SUPPRESS)

    # 軸B
    p.add_argument("--b-rhythm", dest="b_rhythm", type=float, default=0.50)
    p.add_argument("--b-vowel",  dest="b_vowel",  type=float, default=0.50)

    # 軸間
    p.add_argument("--axis-a-weight", dest="axis_a_weight", type=float, default=0.70)
    p.add_argument("--axis-b-weight", dest="axis_b_weight", type=float, default=0.30)

    p.add_argument("--sort-by", dest="sort_by", default="axis_a",
                   help="ソートに使う列名（デフォルト: axis_a）")

    args = p.parse_args()
    main(
        args.input, args.output,
        args.a_len, args.a_open, args.a_sp, args.a_yoon,
        args.b_rhythm, args.b_vowel,
        args.axis_a_weight, args.axis_b_weight,
        args.sort_by,
    )
