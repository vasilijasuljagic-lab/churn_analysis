# Churn Analysis

Churn analysis of the customer workbook in `archive/` (UK full-fibre broadband, 10,000 customers).

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/vasilijasuljagic-lab/churn_analysis.git
cd churn_analysis
pip install -r requirements.txt
```

## Run the dashboard

```bash
python app.py
```

Open http://localhost:5000 — all charts plus a churn-probability calculator.

## Files

Root (everything the app needs):
- `app.py`, `templates/` — Flask dashboard
- `churn_model.py` — `predict_churn(cohort, city, bundle_group, contract, competitors)` API around `churn_model.joblib`
- `churn_model.joblib` — trained pipeline + metrics
- `cleaned_data.csv`, `charts/` — dashboard data and static charts
- `requirements.txt` — dependencies

`archive/` — analysis pipeline and deliverables (not needed to run the app):
- `Case_Study_Data_1.xlsx` — raw input data
- `standalone_analysis.py` — self-contained single-file analysis (run from `archive/`; also works in Jupyter)
- `churn_prediction_analysis.py`, `analysis.py`, `stats_analysis.py`, `build_deck.py` — earlier pipeline scripts
- `Case_Study_Data_1_analysis.xlsx`, `Churn_Analysis.pptx`, `stats_report.md` — outputs
