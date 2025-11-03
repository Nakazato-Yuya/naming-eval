# src/scoring/batch_eval.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Dict

from src.features.epi import evaluate_name


def eval_rows(names: Iterable[str]) -> Iterable[Dict[str, str]]:
    """
    nameのリストを受け取り、EPIおよび各指標を辞書でyieldする。
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


def main(input_csv: str = "data/processed/sample_names.csv",
         output_csv: str = "reports/sample_eval.csv") -> None:
    """
    CSVを読み込んで採点し、CSVで保存する。
    デフォルトの入出力パスはそのまま使える。
    """
    in_path = Path(input_csv)
    out_path = Path(output_csv)

    # 出力先フォルダが無い場合は作成（便利ポイント）
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 入力CSVを読む（UTF-8前提、ヘッダ name）
    with in_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        names = [row.get("name", "") for row in reader]

    # 採点
    rows = list(eval_rows(names))

    # EPI 昇順で並べる（発音しやすい順）
    rows.sort(key=lambda d: float(d["EPI"]))

    # 出力
    fieldnames = ["name", "EPI", "f_len", "f_open", "f_sp", "f_yoon", "M", "mora"]
    with out_path.open("w", encoding="utf-8", newline="") as wf:
        w = csv.DictWriter(wf, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    # ここで引数を受け取れるようにする（★今回の追加ポイント）
    import argparse

    p = argparse.ArgumentParser(description="Batch evaluate EPI from a CSV with a 'name' column.")
    p.add_argument("input", nargs="?", default="data/processed/sample_names.csv",
                   help="入力CSVパス（デフォルト: data/processed/sample_names.csv）")
    p.add_argument("output", nargs="?", default="reports/sample_eval.csv",
                   help="出力CSVパス（デフォルト: reports/sample_eval.csv）")
    args = p.parse_args()

    main(args.input, args.output)
