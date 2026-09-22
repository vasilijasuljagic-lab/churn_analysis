"""Local dashboard: shows all churn charts and a churn-probability calculator.

Run:  python3 app.py   then open http://localhost:5000
"""
from flask import Flask, render_template, request, send_from_directory
from churn_model import predict_churn, get_levels, get_base_rate

app = Flask(__name__)

SECTIONS = [
    ("Descriptive churn analysis", [
        ("termination_reasons.png", "Termination reasons"),
        ("churn_by_contract.png", "Churn rate by contract duration"),
        ("churn_by_city.png", "Churn rate by city"),
        ("churn_by_bundle.png", "Churn rate by bundle speed"),
        ("churn_by_competitors.png", "Churn rate by competitor presence"),
        ("tenure_hist.png", "Tenure: churned vs active"),
        ("churn_time.png", "Churn over time and by activation cohort"),
    ]),
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


@app.route("/charts/<path:name>")
def chart(name):
    return send_from_directory("charts", name)


@app.route("/", methods=["GET", "POST"])
def index():
    levels = get_levels()
    form = {
        "cohort": request.form.get("cohort", levels["Cohort"][-1]),
        "city": request.form.get("city", levels["City"][0]),
        "district": request.form.get("district", ""),
        "contract": request.form.get("contract", levels["Contract"][0]),
        "competitors": request.form.get("competitors", levels["Competitors"][0]),
    }
    if not form["district"] or form["district"] not in levels["District by City"][form["city"]]:
        form["district"] = levels["District by City"][form["city"]][0]
    prob = None
    if request.method == "POST":
        prob = predict_churn(form["cohort"], form["city"], form["district"], form["contract"], form["competitors"])
    return render_template("index.html", sections=SECTIONS, levels=levels, form=form, prob=prob,
                           base_rate=get_base_rate())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
