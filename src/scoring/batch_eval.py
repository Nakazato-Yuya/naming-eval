# --- src/scoring/batch_eval.py ---
import csv, sys, pathlib
from src.features.epi import evaluate_name

def main(inp, outp):
    p_in  = pathlib.Path(inp)
    p_out = pathlib.Path(outp)
    rows = []

    with p_in.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            r = evaluate_name(name)
            rows.append({
                "name": name,
                "EPI": r["EPI"],
                "f_len": r["f_len"],
                "f_open": r["f_open"],
                "f_sp": r["f_sp"],
                "f_yoon": r["f_yoon"],
                "M": r["M"],
                "mora": "|".join(r["mora"]),
            })

    # 小さいほど言いやすい（EPIが低いほど上に）
    rows.sort(key=lambda x: x["EPI"])

    p_out.parent.mkdir(parents=True, exist_ok=True)
    with p_out.open("w", newline='', encoding='utf-8') as g:
        w = csv.DictWriter(g, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv)>1 else "data/processed/sample_names.csv"
    outp = sys.argv[2] if len(sys.argv)>2 else "reports/sample_eval.csv"
    main(inp, outp)
