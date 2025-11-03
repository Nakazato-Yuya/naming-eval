# Naming-Eval

Japanese naming evaluator: ease of pronunciation × adoption trend × distinctiveness.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/utils/check_env.py
pytest -q
```
```bash
# 既定の入出力パスで実行
python -m src.scoring.batch_eval

# または（PYTHONPATH方式）
PYTHONPATH=. python src/scoring/batch_eval.py
```
```bash
python -m src.scoring.batch_eval data/processed/brand_names.csv reports/brand_eval.csv
```
