SHELL := /bin/bash

.PHONY: ui batch test lint smoke

ui:
<TAB>PYTHONPATH=. streamlit run app/app.py

batch:
<TAB>python -m src.scoring.batch_eval data/processed/sample_names.csv reports/sample_eval.csv

test:
<TAB>pytest -q

lint:
<TAB>ruff check src tests

smoke:
<TAB>python -m src.scoring.batch_eval
<TAB>head -n 5 reports/sample_eval.csv
