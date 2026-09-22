"""Local interactive dashboard: filterable churn charts + churn-probability calculator.

Run:  python3 app.py   then open http://localhost:5000
"""
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_from_directory
from churn_model import predict_churn, get_levels, get_base_rate

app = Flask(__name__)

DATA = pd.read_csv("cleaned_data.csv", parse_dates=["Activation Date", "Termination Date"])
DATA["Cohort"] = DATA["Activation Year"].astype(int).astype(str)
DATA["District"] = DATA["Postcode"].astype(str).str.strip().str.upper().str.split().str[0]
DATA["Contract"] = DATA["Contract Duration"].map({0: "Monthly", 12: "12-month", 24: "24-month"})
DATA["Competitors"] = DATA["Number of Competitors"].astype(str)
DATA["Churned"] = DATA["Churned"].astype(int)
DATA["Term Month"] = DATA["Termination Date"].dt.to_period("M").astype(str)

FILTERS = ["City", "Cohort", "Contract", "Competitors", "Bundle"]
BUNDLE_ORDER = ["30Mb", "50Mb", "100/10Mb", "100/20Mb", "150Mb", "250Mb", "500Mb", "750Mb", "1Gb"]
CONTRACT_ORDER = ["Monthly", "12-month", "24-month"]

STATIC_CHARTS = [
    ("Statistical analysis", [
        ("stats_corr_heatmap.png", "Correlation matrix (point-biserial vs churn)"),
        ("stats_cramers_v.png", "Cramér's V — association with churn"),
        ("stats_odds_ratios.png", "Logistic regression odds ratios"),
    ]),
    ("Predictive model", [
        ("stats_roc.png", "ROC curve (hold-out)"),
        ("stats_importance.png", "Permutation importance"),
        ("stats_calibration.png", "Calibration"),
    ]),
]


def filter_options():
    return {
        "City": sorted(DATA["City"].unique()),
        "Cohort": sorted(DATA["Cohort"].unique()),
        "Contract": CONTRACT_ORDER,
        "Competitors": sorted(DATA["Competitors"].unique()),
        "Bundle": [b for b in BUNDLE_ORDER if b in set(DATA["Bundle"])],
    }


def apply_filters(args):
    df = DATA
    for f in FILTERS:
        vals = args.getlist(f)
        if vals:
            df = df[df[f].isin(vals)]
    return df


def rate_by(df, col, order=None):
    g = df.groupby(col)["Churned"].agg(["mean", "count"])
    if order:
        g = g.reindex([o for o in order if o in g.index])
    return {"labels": [str(i) for i in g.index], "rate": [round(v * 100, 1) for v in g["mean"]],
            "n": [int(c) for c in g["count"]]}


@app.route("/api/summary")
def summary():
    df = apply_filters(request.args)
    if df.empty:
        return jsonify({"empty": True})
    ch = df[df["Churned"] == 1]
    reasons = ch["Termination Reason"].value_counts().head(8)
    monthly = ch.groupby("Term Month").size().sort_index()
    tenure_bins = list(range(0, 72, 3))
    t_ch = pd.cut(ch["Tenure Months"], tenure_bins).value_counts().sort_index()
    t_ac = pd.cut(df.loc[df["Churned"] == 0, "Tenure Months"], tenure_bins).value_counts().sort_index()
    return jsonify({
        "kpi": {
            "customers": int(len(df)),
            "churned": int(df["Churned"].sum()),
            "churn_rate": round(df["Churned"].mean() * 100, 1),
            "median_tenure_churned": round(float(ch["Tenure Months"].median()), 1) if len(ch) else None,
            "share_moving": round(float((ch["Termination Reason"] == "Moving Home/Going Away").mean() * 100), 1) if len(ch) else None,
        },
        "by_contract": rate_by(df, "Contract", CONTRACT_ORDER),
        "by_city": rate_by(df, "City"),
        "by_cohort": rate_by(df, "Cohort"),
        "by_competitors": rate_by(df, "Competitors"),
        "by_bundle": rate_by(df, "Bundle", BUNDLE_ORDER),
        "by_district": rate_by(df, "District"),
        "reasons": {"labels": reasons.index.tolist(), "values": [int(v) for v in reasons.values]},
        "monthly": {"labels": monthly.index.tolist(), "values": [int(v) for v in monthly.values]},
        "tenure": {"labels": [f"{b}-{b + 3}" for b in tenure_bins[:-1]],
                   "churned": [int(v) for v in t_ch.values], "active": [int(v) for v in t_ac.values]},
    })


@app.route("/api/predict")
def predict():
    a = request.args
    p = predict_churn(a["cohort"], a["city"], a["district"], a["contract"], a["competitors"])
    return jsonify({"probability": round(p * 100, 1)})


@app.route("/charts/<path:name>")
def chart(name):
    return send_from_directory("charts", name)


@app.route("/")
def index():
    return render_template("index.html", filters=filter_options(), levels=get_levels(),
                           base_rate=round(get_base_rate() * 100, 1), static_charts=STATIC_CHARTS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
