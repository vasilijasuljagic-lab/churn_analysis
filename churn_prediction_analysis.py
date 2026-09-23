"""Hyperoptic churn analysis — consolidated pipeline.

Converted from `Hyperoptic Prediction Analysis.ipynb` with all errors fixed:
- replaced '-' placeholders with NaN before converting Excel serial dates
  (pd.to_datetime(unit='D', origin='1899-12-30') on raw data raised ValueError)
- `Series.isnotnull` -> `Series.notna` (AttributeError)
- `pd.to_datetime` without origin misread Excel serials as nanoseconds
- removed stale `col`/`lower` references and the undefined `competitor_churn` usage
- `import statsmodels as st` removed (unused); proper statsmodels.api import
- seaborn `palette` FutureWarning avoided via `hue`/`legend=False`
- churn tables defined before use; cell ordering made sequential

Outputs: cleaned_data.csv, chart PNGs (charts/), churn_model.joblib,
Case_Study_Data_1_analysis.xlsx (Cleaned Data + Dashboard + Predictive Analytics),
and a console report.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, spearmanr
import statsmodels.api as sm
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XlImage

CHART_DIR = "charts"
XLSX_OUT = "Case_Study_Data_1_analysis.xlsx"
RED, BLUE = "darkred", "steelblue"

# ---------------------------------------------------------------- load + clean
raw = pd.read_excel("Case_Study_Data_1.xlsx", sheet_name="Case Study Data")
df = raw.copy()
for col in ["Activation Date", "Termination Date", "Termination Reason"]:
    df[col] = df[col].mask(df[col] == "-")
df["Activation Date"] = pd.to_datetime(df["Activation Date"], unit="D", origin="1899-12-30")
df["Termination Date"] = pd.to_datetime(df["Termination Date"], unit="D", origin="1899-12-30")

assert (df["Termination Date"] >= df["Activation Date"]).all() or True
bad = df[df["Termination Date"].notna() & (df["Termination Date"] < df["Activation Date"])]
assert len(bad) == 0, "termination before activation"

df["Churn Flag"] = df["Termination Date"].notna().astype(int)
observation_date = df[["Activation Date", "Termination Date"]].max().max()
df["Customer Tenure Days"] = (df["Termination Date"].fillna(observation_date) - df["Activation Date"]).dt.days
df["Customer Tenure Months"] = (df["Customer Tenure Days"] / 30.44).round(1)
df["Tenure Band"] = pd.cut(
    df["Customer Tenure Months"],
    bins=[-1, 3, 6, 12, 24, 36, 48, float("inf")],
    labels=["0–3 months", "3–6 months", "6–12 months", "12–24 months",
            "24–36 months", "36–48 months", "48+ months"],
)
df["Download Mbps"] = df["Bundle"].str.extract(r"^(\d+(?:\.\d+)?)")[0].astype(float)
df.loc[df["Bundle"].str.endswith("Gb"), "Download Mbps"] *= 1000
df["Contract Type"] = df["Contract Duration"].map({0: "Monthly Rolling", 12: "12 Months", 24: "24 Months"})
df["Competitor Band"] = df["Number of Competitors"].map({0: "No Competitors", 1: "1 Competitor", 2: "2 Competitors"})
df["Activation Year"] = df["Activation Date"].dt.year

# keep columns compatible with the app + add new engineered ones
df["Churned"] = df["Churn Flag"]
df["Tenure Months"] = df["Customer Tenure Months"]
df["Term YearMonth"] = df["Termination Date"].dt.to_period("M").astype(str).replace("NaT", np.nan)
df.to_csv("cleaned_data.csv", index=False)

churn_rate = df["Churn Flag"].mean()
print(f"Rows: {len(df)}  Churned: {df['Churn Flag'].sum()}  Overall churn: {churn_rate:.2%}")
print(f"Observation date: {observation_date.date()}")

# ------------------------------------------------- descriptive tables + charts
def churn_table(by):
    t = df.groupby(by, observed=True).agg(Total_Customers=("CustomerID", "count"),
                           Churned_Customers=("Churn Flag", "sum"))
    t["Active_Customers"] = t["Total_Customers"] - t["Churned_Customers"]
    t["Churn_Rate"] = t["Churned_Customers"] / t["Total_Customers"] * 100
    t["Share_of_Total_Churn"] = t["Churned_Customers"] / df["Churn Flag"].sum() * 100
    return t.sort_values("Churn_Rate", ascending=False).round(2)


def labeled_bars(data, x, y, n, title, fname, horizontal=False, ylim=100):
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [RED if v == data[y].max() else BLUE for v in data[y]]
    if horizontal:
        bars = ax.barh(data[x], data[y], color=colors)
        ax.invert_yaxis(); ax.set_xlim(0, ylim); ax.set_xlabel(title)
        for b, v, c in zip(bars, data[y], data[n]):
            ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}%\nn = {c:,}", va="center")
    else:
        bars = ax.bar(data[x].astype(str), data[y], color=colors)
        ax.set_ylim(0, ylim + 12); ax.set_ylabel("Recorded Churn rate (%)")
        for b, v, c in zip(bars, data[y], data[n]):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%\nn = {c:,}", ha="center", va="bottom")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(f"{CHART_DIR}/{fname}", dpi=200, bbox_inches="tight")
    plt.close(fig)


contract_churn = churn_table("Contract Type")
city_churn = churn_table("City")
competitor_churn = churn_table("Competitor Band")
tenure_churn = churn_table("Tenure Band")
reason_analysis = (
    df[df["Churn Flag"] == 1].groupby("Termination Reason")["CustomerID"].count()
    .rename("Churned_Customers").sort_values(ascending=False).to_frame()
)
reason_analysis["Share_of_Churn"] = (reason_analysis["Churned_Customers"] / reason_analysis["Churned_Customers"].sum() * 100).round(2)

labeled_bars(contract_churn.reset_index(), "Contract Type", "Churn_Rate", "Total_Customers",
             "Churn Rate by Contract Type", "nb_contract_churn.png")
labeled_bars(city_churn.reset_index(), "City", "Churn_Rate", "Total_Customers",
             "Churn Rate by City", "nb_city_churn.png", horizontal=True)
labeled_bars(competitor_churn.reset_index(), "Competitor Band", "Churn_Rate", "Total_Customers",
             "Churn Rate by Competitor Presence", "nb_competitor_churn.png")

bundle_churn_all = churn_table("Bundle")
labeled_bars(bundle_churn_all.reset_index(), "Bundle", "Churn_Rate", "Total_Customers",
             "Churn Rate by Bundle", "nb_bundle_churn_all.png")

cohort_churn = (df.groupby("Activation Year")["Churn Flag"].agg(["mean", "size"]).reset_index()
                  .rename(columns={"mean": "Churn_Rate", "size": "Total_Customers"}))
cohort_churn["Churn_Rate"] *= 100
labeled_bars(cohort_churn, "Activation Year", "Churn_Rate", "Total_Customers",
             "Churn Rate by Activation Cohort", "nb_cohort_churn.png")

monthly_churn = df.dropna(subset=["Termination Date"]).set_index("Termination Date").resample("ME").size()
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(monthly_churn.index, monthly_churn.values, marker="o")
ax.set_title("Recorded Churn Events per Month"); ax.set_xlabel("Month"); ax.set_ylabel("Churn Events")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/nb_monthly_churn.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 6))
for subset, color, label in [(1, "red", "Churned"), (0, "gray", "Active")]:
    ax.hist(df.loc[df["Churn Flag"] == subset, "Customer Tenure Months"],
            bins=30, density=True, alpha=0.5, color=color, label=label)
ax.set_title("Customer Tenure Distribution: Active vs Churned"); ax.legend()
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/nb_tenure_hist.png", dpi=200); plt.close(fig)

same_day = df[df["Termination Date"].notna() & (df["Termination Date"] == df["Activation Date"])]
print(f"Same-day activation+termination: {len(same_day)}")

# ------------------------------------------------------------- statistics
def cramers_v(col):
    t = pd.crosstab(df[col], df["Churn Flag"])
    chi2, p, dof, _ = chi2_contingency(t)
    v = np.sqrt((chi2 / t.to_numpy().sum()) / (min(t.shape) - 1))
    return chi2, p, dof, v


stat_rows = []
for col in ["City", "Contract Type", "Competitor Band", "Bundle"]:
    chi2, p, dof, v = cramers_v(col)
    stat_rows.append({"Factor": col, "Chi2": round(chi2, 1), "p_value": p, "dof": dof, "Cramers_V": round(v, 3)})
    print(f"{col}: chi2={chi2:.1f} p={p:.2e} V={v:.3f}")
stats_table = pd.DataFrame(stat_rows)
rho, p_rho = spearmanr(df["Customer Tenure Months"], df["Churn Flag"])
print(f"Spearman tenure×churn: rho={rho:.3f} p={p_rho:.2e}")

# --------------------------------------------------------------- model data
MAJOR_BUNDLES = ["50Mb", "150Mb", "500Mb", "1Gb"]
model_data = df[["Churn Flag", "Contract Type", "City", "Bundle",
                 "Number of Competitors", "Activation Year"]].copy()
model_data["Bundle Group"] = model_data["Bundle"].where(model_data["Bundle"].isin(MAJOR_BUNDLES), "Other")
model_data = model_data.drop(columns=["Bundle"])

FEATURES = ["Contract Type", "City", "Bundle Group", "Number of Competitors", "Activation Year"]

# --- statsmodels logit (inference: odds ratios), dummies with drop_first
X_sm = pd.get_dummies(model_data[FEATURES].astype(str), drop_first=True, dtype=int)
X_sm = sm.add_constant(X_sm)
logit = sm.Logit(model_data["Churn Flag"], X_sm).fit(disp=0)
odds_ratio_table = pd.DataFrame({
    "Odds Ratio": np.exp(logit.params).round(3),
    "CI Lower": np.exp(logit.conf_int()[0]).round(3),
    "CI Upper": np.exp(logit.conf_int()[1]).round(3),
    "p-value": logit.pvalues.round(4),
}).round(3)
print(odds_ratio_table)

# --- sklearn pipeline (predictive: stratified holdout)
X, y = model_data[FEATURES], model_data["Churn Flag"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)
pipe = Pipeline([
    ("preprocessor", ColumnTransformer(
        [("categorical", OneHotEncoder(handle_unknown="ignore"), FEATURES)], remainder="drop")),
    ("classifier", LogisticRegression(max_iter=1000)),
])
pipe.fit(Xtr, ytr)
yp, yprob = pipe.predict(Xte), pipe.predict_proba(Xte)[:, 1]
cm = confusion_matrix(yte, yp)
metrics = {"accuracy": accuracy_score(yte, yp), "precision": precision_score(yte, yp),
           "recall": recall_score(yte, yp), "roc_auc": roc_auc_score(yte, yprob)}
print({k: round(v, 3) for k, v in metrics.items()})

# --- robustness: model without Activation Year
FEATURES_NY = [f for f in FEATURES if f != "Activation Year"]
Xtr2, Xte2, ytr2, yte2 = train_test_split(
    model_data[FEATURES_NY], y, test_size=0.20, random_state=42, stratify=y)
pipe_ny = Pipeline([
    ("preprocessor", ColumnTransformer(
        [("categorical", OneHotEncoder(handle_unknown="ignore"), FEATURES_NY)], remainder="drop")),
    ("classifier", LogisticRegression(max_iter=1000)),
])
pipe_ny.fit(Xtr2, ytr2)
yp2, yprob2 = pipe_ny.predict(Xte2), pipe_ny.predict_proba(Xte2)[:, 1]
metrics_ny = {"accuracy": accuracy_score(yte2, yp2), "precision": precision_score(yte2, yp2),
              "recall": recall_score(yte2, yp2), "roc_auc": roc_auc_score(yte2, yprob2)}
print({k: round(v, 3) for k, v in metrics_ny.items()})

# --------------------------------------------- saved model for the dashboard
levels = {
    "Contract Type": sorted(model_data["Contract Type"].unique()),
    "City": sorted(model_data["City"].unique()),
    "Bundle Group": sorted(model_data["Bundle Group"].unique()),
    "Number of Competitors": sorted(model_data["Number of Competitors"].unique().astype(str)),
    "Activation Year": sorted(model_data["Activation Year"].unique().astype(str)),
}
pipe.fit(X, y)  # refit on all data for the deployed artifact
joblib.dump({
    "model": pipe,
    "features": FEATURES,
    "levels": levels,
    "base_rate": float(churn_rate * 100),
    "metrics": metrics,
    "metrics_no_year": metrics_ny,
    "odds_ratios": odds_ratio_table,
    "confusion_matrix": cm.tolist(),
}, "churn_model.joblib")
print("Saved churn_model.joblib")

# ---------------------------------------------------- Excel: Dashboard+Predict
from openpyxl.utils.dataframe import dataframe_to_rows

xl_charts = [
    ("nb_contract_churn.png", "B7"), ("nb_competitor_churn.png", "J7"),
    ("nb_city_churn.png", "B25"), ("nb_bundle_churn_all.png", "J25"),
    ("nb_cohort_churn.png", "B43"), ("nb_monthly_churn.png", "J43"),
    ("nb_tenure_hist.png", "B61"),
]

with pd.ExcelWriter(XLSX_OUT, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Cleaned Data", index=False)

wb = load_workbook(XLSX_OUT)
ws = wb.create_sheet("Dashboard")
for fname, cell in xl_charts:
    img = XlImage(f"{CHART_DIR}/{fname}")
    img.width, img.height = 800, 500
    ws.add_image(img, cell)

wp = wb.create_sheet("Predictive Analytics")

def write_table(ws, df_out, start_row, title, index_name=None):
    ws.cell(row=start_row, column=1, value=title)
    r = start_row + 1
    frame = df_out.copy()
    if index_name is not None:
        frame.insert(0, index_name, frame.index.astype(str))
    for j, col in enumerate(frame.columns, start=1):
        ws.cell(row=r, column=j, value=str(col))
    for i, row in enumerate(frame.itertuples(index=False), start=r + 1):
        for j, val in enumerate(row, start=1):
            ws.cell(row=i, column=j, value=float(val) if isinstance(val, (np.floating,)) else val)
    return r + len(frame) + 2

r = 2
kpi = pd.DataFrame({
    "Metric": ["Accuracy", "Precision", "Recall", "ROC-AUC",
               "No-Year Accuracy", "No-Year Precision", "No-Year Recall", "No-Year ROC-AUC"],
    "Value": [metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["roc_auc"],
              metrics_ny["accuracy"], metrics_ny["precision"], metrics_ny["recall"], metrics_ny["roc_auc"]],
}).round(3)
r = write_table(wp, kpi, r, "MODEL METRICS (logistic regression, 20% stratified holdout; second block = without Activation Year)")

cm_df = pd.DataFrame(cm, index=["Actual: No Churn", "Actual: Churn"],
                     columns=["Predicted: No Churn", "Predicted: Churn"])
r = write_table(wp, cm_df, r, "CONFUSION MATRIX (test set)", index_name="")
r = write_table(wp, odds_ratio_table, r, "ODDS RATIOS (statsmodels Logit; reference = first level of each factor)", index_name="Term")
r = write_table(wp, stats_table, r, "CHI-SQUARE + CRAMÉR'S V (factor vs churn)")
r = write_table(wp, contract_churn, r, "CHURN BY CONTRACT TYPE", index_name="Contract Type")
r = write_table(wp, city_churn, r, "CHURN BY CITY", index_name="City")
r = write_table(wp, cohort_churn.set_index("Activation Year"), r, "CHURN BY ACTIVATION COHORT", index_name="Activation Year")
r = write_table(wp, tenure_churn, r, "CHURN BY TENURE BAND", index_name="Tenure Band")
r = write_table(wp, reason_analysis, r, "TERMINATION REASONS (churned only)", index_name="Termination Reason")
wb.save(XLSX_OUT)
print(f"Saved {XLSX_OUT}")
