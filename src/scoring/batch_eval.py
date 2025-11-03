# src/scoring/batch_eval.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Dict, List

import pandas as pd

# 1件のEPI計算ロジック（既存実装を利用）
from src.features.epi import evaluate_name

# =========================
# UI/CLI 共通：重みと評価関数
# =========================

@dataclass
class Weights:
    w_len: float = 0.25
    w_open: float = 0.25
    w_sp: float = 0.25
    w_yoon: float = 0.25


def _ensure_features(row: Dict[str, object]) -> Dict[str, float]:
    """
    row に f_len, f_open, f_sp, f_yoon が無ければ name から evaluate_name で生成。
    既に列がある場合はそれを優先（0–1想定）。
    """
    out: Dict[str, float] = {}
    if "f_len" in row and "f_open" in row and "f_sp" in row and "f_yoon" in row:
        out["name"] = str(row.get("name", ""))
        out["f_len"]  = float(row.get("f_len", 0.0))
        out["f_open"] = float(row.get("f_open", 0.0))
        out["f_sp"]   = float(row.get("f_sp", 0.0))
        out["f_yoon"] = float(row.get("f_yoon", 0.0))
        # 任意フィールド（存在すれば反映）
        out["M"]    = int(row.get("M", 0)) if row.get("M", "") != "" else 0
        mora_val = row.get("mora", [])
        if isinstance(mora_val, str):
            # 既存CSV互換で '|' 連結文字列が来た場合
            mora_val = [m for m in mora_val.split("|") if m]
        out["mora"] = list(mora_val) if isinstance(mora_val, (list, tuple)) else []
        return out

    # 無ければ name から計算
    name = str(row.get("name", "") or "").strip()
    r = evaluate_name(name) if name else {
        "name": "", "EPI": 0.0, "f_len": 0.0, "f_open": 0.0, "f_sp": 0.0, "f_yoon": 0.0, "M": 0, "mora": []
    }
    return {
        "name":  r["name"],
        "f_len": float(r["f_len"]),
        "f_open":float(r["f_open"]),
        "f_sp":  float(r.get("f_sp", 0.0)),
        "f_yoon":float(r.get("f_yoon", 0.0)),
        "M":     int(r.get("M", 0)),
        "mora":  list(r.get("mora", [])),
    }


def _score_from_features(feat: Dict[str, float], w: Weights) -> Dict[str, float]:
    """サブ指標と重みから EPI（線形合成）を計算。"""
    f_len  = float(feat["f_len"])
    f_open = float(feat["f_open"])
    f_sp   = float(feat["f_sp"])
    f_yoon = float(feat["f_yoon"])
    epi = w.w_len*f_len + w.w_open*f_open + w.w_sp*f_sp + w.w_yoon*f_yoon
    return {"EPI": float(epi)}


def evaluate_df(df: pd.DataFrame, w: Weights) -> pd.DataFrame:
    """
    DataFrame → DataFrame の評価（UI/ノートブック/CLIの共有部）。
    - 列に f_* が無ければ name から自動計算。
    - 将来 UR / C-PhonoScore をここで合成して FinalScore を更新。
    """
    records = df.to_dict(orient="records")
    out_rows: List[Dict[str, object]] = []
    for r in records:
        feat = _ensure_features(r)
        sc = _score_from_features(feat, w)
        row = {**r, **feat, **sc}
        row["FinalScore"] = row["EPI"]  # TODO: 将来 UR/C-Phono で更新
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def evaluate_names_to_df(names: List[str], w: Weights) -> pd.DataFrame:
    """UI で名前だけのリストを渡したいときのヘルパー。"""
    base = [{"name": (n or "").strip()} for n in names if (n or "").strip()]
    return evaluate_df(pd.DataFrame(base), w)

# =========================
# レガシー互換：CSV書式 I/O
# =========================

def _to_legacy_csv(df_out: pd.DataFrame, out_path: Path) -> None:
    """
    evaluate_df の結果を従来の CSV 形式（文字列化 & mora='|'連結）で書き出す。
    """
    cols = ["name", "EPI", "f_len", "f_open", "f_sp", "f_yoon", "M", "mora"]
    df = df_out.copy()

    # mora を '|' 連結
    if "mora" in df.columns:
        df["mora"] = df["mora"].apply(
            lambda x: "|".join(x) if isinstance(x, (list, tuple)) else (x if isinstance(x, str) else "")
        )
    else:
        df["mora"] = ""

    # 欠けている列を補完して順序固定
    for c in cols:
        if c not in df.columns:
            df[c] = ""
        # 従来互換として文字列化
        df[c] = df[c].astype(str)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(out_path, index=False, encoding="utf-8")


# 旧API（比較/検証用に残す。mainでは未使用）
def eval_rows(names: Iterable[str]) -> Iterable[Dict[str, str]]:
    """
    name のリストを受け取り、EPIおよび各指標を辞書で yield。
    （従来の下流を壊さないよう str 化）
    """
    for name in names:
        name = (name or "").strip()
        if not name:
            continue
        r = evaluate_name(name)
        yield {
            "name": r["name"],
            "EPI": str(r["EPI"]),
            "f_len": str(r["f_len"]),
            "f_open": str(r["f_open"]),
            "f_sp": str(r.get("f_sp", 0.0)),
            "f_yoon": str(r.get("f_yoon", 0.0)),
            "M": str(r["M"]),
            "mora": "|".join(r["mora"]),
        }


def main(
    input_csv: str = "data/processed/sample_names.csv",
    output_csv: str = "reports/sample_eval.csv",
    w_len: float = 0.25,
    w_open: float = 0.25,
    w_sp: float = 0.25,
    w_yoon: float = 0.25,
    sort_by_epi: bool = True,
) -> None:
    """
    CSVを読み込んで evaluate_df(Weights) で採点し、従来互換のCSVを書き出す。
    """
    in_path = Path(input_csv)
    out_path = Path(output_csv)

    # 入力（UTF-8）
    df_in = pd.read_csv(in_path, encoding="utf-8")

    # 採点（UIと同じ評価経路）
    w = Weights(w_len=w_len, w_open=w_open, w_sp=w_sp, w_yoon=w_yoon)
    df_eval = evaluate_df(df_in, w)

    # 並べ替え（EPI昇順＝発音しやすい順）
    if sort_by_epi and "EPI" in df_eval.columns:
        df_eval = df_eval.sort_values("EPI", ascending=True).reset_index(drop=True)

    # 従来形式で出力
    _to_legacy_csv(df_eval, out_path)
    print(f"評価結果を {out_path} に保存しました。")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(
        description="Batch evaluate EPI from a CSV with a 'name' column."
    )
    p.add_argument("input", nargs="?", default="data/processed/sample_names.csv",
                   help="入力CSVパス（デフォルト: data/processed/sample_names.csv）")
    p.add_argument("output", nargs="?", default="reports/sample_eval.csv",
                   help="出力CSVパス（デフォルト: reports/sample_eval.csv）")

    # 重み（UIと同じ意味）
    p.add_argument("--w-len",  dest="w_len",  type=float, default=0.25, help="f_len の重み")
    p.add_argument("--w-open", dest="w_open", type=float, default=0.25, help="f_open の重み")
    p.add_argument("--w-sp",   dest="w_sp",   type=float, default=0.25, help="f_sp の重み")
    p.add_argument("--w-yoon", dest="w_yoon", type=float, default=0.25, help="f_yoon の重み")

    p.add_argument("--no-sort", dest="sort_by_epi", action="store_false",
                   help="EPIでの昇順ソートを無効化")

    args = p.parse_args()
    main(args.input, args.output, args.w_len, args.w_open, args.w_sp, args.w_yoon, args.sort_by_epi)


