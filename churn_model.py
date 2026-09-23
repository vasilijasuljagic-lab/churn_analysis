"""Reusable churn prediction interface for the local churn-calculator app.

Model trained by churn_prediction_analysis.py (logistic regression on
Contract Type, City, Bundle Group, Number of Competitors, Activation Year).

Usage:
    from churn_model import predict_churn, get_levels
    p = predict_churn(cohort="2024", city="London", bundle_group="1Gb",
                      contract="24 Months", competitors=1)
"""
from functools import lru_cache
import pandas as pd
import joblib

MODEL_PATH = "churn_model.joblib"


@lru_cache(maxsize=1)
def _bundle():
    return joblib.load(MODEL_PATH)


def get_levels():
    """Valid values for every factor."""
    return _bundle()["levels"]


def get_base_rate():
    """Churn rate of the training sample."""
    return _bundle()["base_rate"]


def get_metrics():
    """Hold-out metrics for the model (and the no-year robustness check)."""
    b = _bundle()
    return {"metrics": b["metrics"], "metrics_no_year": b["metrics_no_year"]}


def predict_churn(cohort, city, bundle_group, contract, competitors):
    """Return P(churn) for one customer profile.

    contract: 'Monthly Rolling' | '12 Months' | '24 Months'
    bundle_group: '50Mb' | '150Mb' | '500Mb' | '1Gb' | 'Other'
    """
    b = _bundle()
    row = pd.DataFrame([{
        "Contract Type": contract,
        "City": city,
        "Bundle Group": bundle_group,
        "Number of Competitors": int(competitors),
        "Activation Year": int(cohort),
    }])[b["features"]]
    return float(b["model"].predict_proba(row)[0, 1])


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 6:
        print(f"P(churn) = {predict_churn(*sys.argv[1:]):.3f}")
    else:
        print("usage: python churn_model.py <cohort> <city> <bundle_group> <contract> <competitors>")
        print("levels:", get_levels())
