.PHONY: setup ui batch test lint
setup:
\tpython -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
ui:
\tPYTHONPATH=. streamlit run app/app.py
batch:
\tpython -m src.scoring.batch_eval data/processed/sample_names.csv reports/sample_eval.csv
test:
\tpytest -q
lint:
\truff check src tests
