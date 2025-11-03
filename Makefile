SHELL := /bin/bash

.PHONY: ui batch test lint smoke

ui:
	PYTHONPATH=. streamlit run app/app.py

batch:
	python -m src.scoring.batch_eval data/processed/sample_names.csv reports/sample_eval.csv

test:
	pytest -q

lint:
	ruff check src tests

smoke:
	python -m src.scoring.batch_eval
	head -n 5 reports/sample_eval.csv
