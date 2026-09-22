# Churn Analysis

Churn analysis of `Case_Study_Data_1.xlsx` (UK full-fibre broadband, 10,000 customers).

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

## Regenerate the analysis

```bash
python analysis.py        # cleaning, descriptive charts -> cleaned_data.csv, charts/
python stats_analysis.py  # correlations, logistic regression, predictive model -> stats_report.md, churn_model.joblib
python build_deck.py      # PowerPoint -> Churn_Analysis.pptx
```

## Files

- `analysis.py` / `stats_analysis.py` / `build_deck.py` — analysis scripts
- `churn_model.py` — `predict_churn(cohort, city, district, contract, competitors)` API around `churn_model.joblib`
- `app.py`, `templates/` — Flask dashboard
- `stats_report.md` — statistical findings
- `Churn_Analysis.pptx` — presentation
