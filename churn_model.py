"""Reusable churn prediction interface for the future local churn-calculator app.

Usage:
    from churn_model import predict_churn, get_levels
    p = predict_churn(cohort=2024, city="London", district="E14", contract="24-month", competitors=1)
"""
from functools import lru_cache
import pandas as pd
import joblib

MODEL_PATH = "churn_model.joblib"


@lru_cache(maxsize=1)
def _bundle():
    return joblib.load(MODEL_PATH)


def get_levels():
    """Valid values for every factor, plus districts grouped by city."""
    return _bundle()["levels"]


def predict_churn(cohort, city, district, contract, competitors):
    """Return P(churn) for one customer profile. Contract: 'Monthly' | '12-month' | '24-month'."""
    b = _bundle()
    row = pd.DataFrame([{
        "Cohort": str(cohort),
        "City": city,
        "District": district,
        "Contract": contract,
        "Competitors": str(competitors),
    }])[b["features"]]
    return float(b["model"].predict_proba(row)[0, 1])


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 6:
        print(f"P(churn) = {predict_churn(*sys.argv[1:]):.3f}")
    else:
        print("usage: python churn_model.py <cohort> <city> <district> <contract> <competitors>")
        print("levels:", get_levels())
