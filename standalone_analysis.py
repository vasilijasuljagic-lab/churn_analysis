"""Standalone Hyperoptic churn analysis — single self-contained file.

USAGE (Jupyter notebook)
    Put `Case_Study_Data_1.xlsx` in the same folder as your notebook, then run
    the whole file in a cell (e.g. `%run standalone_analysis.py` or paste it).
    If your file is still named "Case Study Data 1.xlsx" (spaces), that's fine
    too — the loader tries both names. Or set DATA_FILE below to the full path.

USAGE (terminal)
    1. Put this file next to `Case_Study_Data_1.xlsx`
    2. pip install pandas numpy matplotlib scipy statsmodels scikit-learn openpyxl
    3. python standalone_analysis.py

It needs NOTHING else from the repository — no other scripts, no model files.
It prints every result to the console (descriptive tables, statistical tests,
model metrics, odds ratios) and writes two files next to it:
  charts/*.png                 — labeled bar charts for each factor
  Case_Study_Data_1_analysis.xlsx — Cleaned Data + Dashboard + Predictive Analytics

Same pipeline as churn_prediction_analysis.py (converted from the notebook
"Hyperoptic Prediction Analysis.ipynb"), minus the Flask-app plumbing.

Flow: Part 1 data prep -> Part 2 descriptive -> statistics -> Part 3
predictive (inference + holdout + robustness) -> Part 4 Excel outputs ->
Part 5 prescriptive summary.
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# In Jupyter the default (inline) backend shows each chart right after its
# step; as a plain script we use the headless Agg backend so figures save to
# PNG without needing a display. plt.show() below is a no-op under Agg.
try:
    get_ipython  # type: ignore[name-defined]
    IN_JUPYTER = True
except NameError:
    matplotlib.use("Agg")
    IN_JUPYTER = False
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
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XlImage

import os
os.makedirs("charts", exist_ok=True)

CHART_DIR = "charts"
XLSX_OUT = "Case_Study_Data_1_analysis.xlsx"

# --- data file location ------------------------------------------------------
# Change this if your Excel file lives somewhere else, e.g.
#   DATA_FILE = r"C:\Users\you\Downloads\Case Study Data 1.xlsx"
#   DATA_FILE = "/home/you/Downloads/Case Study Data 1.xlsx"
# Otherwise the loader searches the current folder (the notebook/script's
# folder) under both names, with and without spaces.
DATA_FILE = "Case_Study_Data_1.xlsx"


def resolve_data_file():
    """Find the Excel input: exact DATA_FILE first, then the spaced variant
    'Case Study Data 1.xlsx', in the working directory and next to this script
    (script dir is skipped in Jupyter, where __file__ doesn't exist)."""
    names = [DATA_FILE, "Case_Study_Data_1.xlsx", "Case Study Data 1.xlsx"]
    dirs = [os.getcwd()]
    try:
        dirs.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:  # Jupyter has no __file__
        pass
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise FileNotFoundError(
        f"Could not find the Excel file. Put 'Case_Study_Data_1.xlsx' in "
        f"{os.getcwd()} (the folder Jupyter is running in), or set DATA_FILE "
        f"at the top of standalone_analysis.py to its full path.")


DATA_PATH = resolve_data_file()
RED, BLUE = "darkred", "steelblue"

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)


def show(title, obj):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(obj)


# ---------------------------------------------------------------- load + clean
# PART 1: DATA PREPARATION
#
# Load the raw customer export. The workbook has two sheets; "Case Study Data"
# holds the 10,000 customer records, "Fields Description" is the data dictionary.
#
# Missingness: the only missing values are in Termination Date and Termination
# Reason. Missing termination = the customer is still active, so the missingness
# is meaningful (it IS the churn flag), not missing-at-random. No duplicates were
# found, and no numeric outliers worth removing (Number of Competitors is a
# bounded 0-2 field; the IQR screen in the notebook flagged nothing real).
raw = pd.read_excel(DATA_PATH, sheet_name="Case Study Data")
df = raw.copy()
# '-' is used in the export as a text placeholder where a date is missing;
# it must be turned into real NaN BEFORE parsing dates, otherwise the
# serial-date conversion fails on those strings. pd.to_numeric is needed
# because the masked column is object dtype, which to_datetime rejects.
for col in ["Activation Date", "Termination Date", "Termination Reason"]:
    df[col] = df[col].mask(df[col] == "-")
df["Activation Date"] = pd.to_datetime(pd.to_numeric(df["Activation Date"]), unit="D", origin="1899-12-30")
df["Termination Date"] = pd.to_datetime(pd.to_numeric(df["Termination Date"]), unit="D", origin="1899-12-30")

# sanity check: no termination may come before activation (expected 0)
bad = df[df["Termination Date"].notna() & (df["Termination Date"] < df["Activation Date"])]
assert len(bad) == 0, "termination before activation"

df["Churn Flag"] = df["Termination Date"].notna().astype(int)

# Latest observed date in the dataset. For non-churned customers we measure
# tenure as of the end of the observation period; for churned customers it is
# simply Termination Date - Activation Date.
observation_date = df[["Activation Date", "Termination Date"]].max().max()
df["Customer Tenure Days"] = (df["Termination Date"].fillna(observation_date) - df["Activation Date"]).dt.days
df["Customer Tenure Months"] = (df["Customer Tenure Days"] / 30.44).round(1)
# Tenure bands used in the descriptive layer. Note: the shortest bands
# (0-3, 3-6 months) show 100% recorded churn — this is partly a construction
# artifact: a still-active customer cannot yet appear in a short band, so the
# bands only contain customers who terminated that early. The ~1,070 real
# early churners are still worth an onboarding look.
df["Tenure Band"] = pd.cut(
    df["Customer Tenure Months"],
    bins=[-1, 3, 6, 12, 24, 36, 48, float("inf")],
    labels=["0–3 months", "3–6 months", "6–12 months", "12–24 months",
            "24–36 months", "36–48 months", "48+ months"],
)
df["Download Mbps"] = df["Bundle"].str.extract(r"^(\d+(?:\.\d+)?)")[0].astype(float)
df.loc[df["Bundle"].str.endswith("Gb"), "Download Mbps"] *= 1000
# New categorical columns: map numeric Contract Duration to a readable label,
# and band the 0-2 Number of Competitors field.
df["Contract Type"] = df["Contract Duration"].map({0: "Monthly Rolling", 12: "12 Months", 24: "24 Months"})
df["Competitor Band"] = df["Number of Competitors"].map({0: "No Competitors", 1: "1 Competitor", 2: "2 Competitors"})
df["Activation Year"] = df["Activation Date"].dt.year

churn_rate = df["Churn Flag"].mean()
show("DATASET OVERVIEW", (
    f"Rows: {len(df):,}   Churned: {int(df['Churn Flag'].sum()):,}   "
    f"Active: {int((1 - df['Churn Flag']).sum()):,}\n"
    f"Recorded churn rate: {churn_rate:.2%}\n"
    f"Observation date (latest activation/termination): {observation_date.date()}"
))

same_day = df[df["Termination Date"].notna() & (df["Termination Date"] == df["Activation Date"])]
show("SAME-DAY ACTIVATION + TERMINATION", f"{len(same_day)} customers churned on their activation day")

# ------------------------------------------------- descriptive tables + charts
# PART 2: DESCRIPTIVE ANALYTICS — what happened, and where churn concentrates.
#
# One helper produces every churn table the same way: Total / Churned /
# Active / Churn_Rate / Share_of_Total_Churn per group. observed=True keeps
# the groupby to categories actually present (the default observed=False
# pads results with empty category combinations).
def churn_table(by):
    t = df.groupby(by, observed=True).agg(Total_Customers=("CustomerID", "count"),
                           Churned_Customers=("Churn Flag", "sum"))
    t["Active_Customers"] = t["Total_Customers"] - t["Churned_Customers"]
    t["Churn_Rate"] = t["Churned_Customers"] / t["Total_Customers"] * 100
    t["Share_of_Total_Churn"] = t["Churned_Customers"] / df["Churn Flag"].sum() * 100
    return t.sort_values("Churn_Rate", ascending=False).round(2)


# One helper produces every bar chart the same way, matching the notebook's
# style: highest-churn bar in red, others steelblue, and a data label on each
# bar with the churn percentage on top and the customer count (n) below.
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
    plt.show()  # displays inline in Jupyter; no-op in a script
    plt.close(fig)


# CHURN TABLES
# 1. By contract type — 24-month customers churn substantially less than
#    12-month / monthly rolling. Tenure also differs: 24-month customers have
#    roughly twice the median observed tenure, so part of the gap is contract
#    mechanics (still in-contract), not only satisfaction.
contract_churn = churn_table("Contract Type")
show("CHURN BY CONTRACT TYPE", contract_churn)
city_churn = churn_table("City")
show("CHURN BY CITY", city_churn)
competitor_churn = churn_table("Competitor Band")
show("CHURN BY COMPETITOR PRESENCE", competitor_churn)
tenure_churn = churn_table("Tenure Band")
show("CHURN BY TENURE BAND (see artifact note above)", tenure_churn)

reason_analysis = (
    df[df["Churn Flag"] == 1].groupby("Termination Reason")["CustomerID"].count()
    .rename("Churned_Customers").sort_values(ascending=False).to_frame()
)
reason_analysis["Share_of_Churn"] = (reason_analysis["Churned_Customers"] / reason_analysis["Churned_Customers"].sum() * 100).round(2)
show("TERMINATION REASONS (churned customers only)", reason_analysis)
# Note on "Customer not leaving" (521 records, 7.5% of churn): it appears among
# rows our flag treats as churned, so recorded termination is not necessarily
# customer-initiated. Its tenure/contract/competitor/city/bundle mix closely
# matches the overall churned population — kept, but meaning stays ambiguous.

labeled_bars(contract_churn.reset_index(), "Contract Type", "Churn_Rate", "Total_Customers",
             "Churn Rate by Contract Type", "nb_contract_churn.png")
labeled_bars(city_churn.reset_index(), "City", "Churn_Rate", "Total_Customers",
             "Churn Rate by City", "nb_city_churn.png", horizontal=True)
labeled_bars(competitor_churn.reset_index(), "Competitor Band", "Churn_Rate", "Total_Customers",
             "Churn Rate by Competitor Presence", "nb_competitor_churn.png")

bundle_churn_all = churn_table("Bundle")
show("CHURN BY BUNDLE", bundle_churn_all)
labeled_bars(bundle_churn_all.reset_index(), "Bundle", "Churn_Rate", "Total_Customers",
             "Churn Rate by Bundle", "nb_bundle_churn_all.png")

cohort_churn = (df.groupby("Activation Year")["Churn Flag"].agg(["mean", "size"]).reset_index()
                  .rename(columns={"mean": "Churn_Rate", "size": "Total_Customers"}))
cohort_churn["Churn_Rate"] *= 100
show("CHURN BY ACTIVATION COHORT", cohort_churn.set_index("Activation Year"))
labeled_bars(cohort_churn, "Activation Year", "Churn_Rate", "Total_Customers",
             "Churn Rate by Activation Cohort", "nb_cohort_churn.png")

monthly_churn = df.dropna(subset=["Termination Date"]).set_index("Termination Date").resample("ME").size()
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(monthly_churn.index, monthly_churn.values, marker="o")
ax.set_title("Recorded Churn Events per Month"); ax.set_xlabel("Month"); ax.set_ylabel("Churn Events")
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/nb_monthly_churn.png", dpi=200); plt.show(); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 6))
for subset, color, label in [(1, "red", "Churned"), (0, "gray", "Active")]:
    ax.hist(df.loc[df["Churn Flag"] == subset, "Customer Tenure Months"],
            bins=30, density=True, alpha=0.5, color=color, label=label)
ax.set_title("Customer Tenure Distribution: Active vs Churned"); ax.legend()
fig.tight_layout(); fig.savefig(f"{CHART_DIR}/nb_tenure_hist.png", dpi=200); plt.show(); plt.close(fig)

# ------------------------------------------------------------- statistics
# STATISTICAL LAYER — are the group differences real, or noise?
#
# For categorical factor vs binary churn we use the chi-square test of
# independence plus Cramer's V for effect size (0-1: how strong the
# association is, not just whether it is significant — with n=10,000 almost
# everything is "significant", so V is the meaningful number).
def cramers_v(col):
    t = pd.crosstab(df[col], df["Churn Flag"])
    chi2, p, dof, _ = chi2_contingency(t)
    v = np.sqrt((chi2 / t.to_numpy().sum()) / (min(t.shape) - 1))
    return chi2, p, dof, v


stat_rows = []
for col in ["City", "Contract Type", "Competitor Band", "Bundle"]:
    chi2, p, dof, v = cramers_v(col)
    stat_rows.append({"Factor": col, "Chi2": round(chi2, 1), "p_value": p, "dof": dof, "Cramers_V": round(v, 3)})
stats_table = pd.DataFrame(stat_rows)
show("CHI-SQUARE + CRAMER'S V (factor vs churn)", stats_table.to_string(index=False))

# Spearman (rank) correlation tenure vs churn — monotone association, robust
# to the skewed tenure distribution. Negative rho = longer tenure, less churn.
rho, p_rho = spearmanr(df["Customer Tenure Months"], df["Churn Flag"])
show("SPEARMAN TENURE x CHURN", f"rho = {rho:.3f}   p = {p_rho:.2e}")

# --------------------------------------------------------------- model data
# PART 3: PREDICTIVE ANALYTICS — can we predict which customers will churn?
#
# Feature set: contract type, city, bundle group, number of competitors,
# activation year (cohort). Bundle is collapsed to the four major bundles
# plus "Other" — the niche bundles have single-digit row counts and would
# only add noise as model features.
MAJOR_BUNDLES = ["50Mb", "150Mb", "500Mb", "1Gb"]
model_data = df[["Churn Flag", "Contract Type", "City", "Bundle",
                 "Number of Competitors", "Activation Year"]].copy()
model_data["Bundle Group"] = model_data["Bundle"].where(model_data["Bundle"].isin(MAJOR_BUNDLES), "Other")
model_data = model_data.drop(columns=["Bundle"])

FEATURES = ["Contract Type", "City", "Bundle Group", "Number of Competitors", "Activation Year"]

# --- statsmodels logit (inference: odds ratios), dummies with drop_first
# First the inferential view: a logistic regression on dummy variables
# (drop_first gives each factor a reference level). The odds ratio per level
# is the interpretable output — e.g. 0.22 for 24 Months means ~78% lower odds
# of churn vs the 12-month reference, all else equal.
X_sm = pd.get_dummies(model_data[FEATURES].astype(str), drop_first=True, dtype=int)
X_sm = sm.add_constant(X_sm)
logit = sm.Logit(model_data["Churn Flag"], X_sm).fit(disp=0)
odds_ratio_table = pd.DataFrame({
    "Odds Ratio": np.exp(logit.params).round(3),
    "CI Lower": np.exp(logit.conf_int()[0]).round(3),
    "CI Upper": np.exp(logit.conf_int()[1]).round(3),
    "p-value": logit.pvalues.round(4),
}).round(3)
show("ODDS RATIOS (reference = first level of each factor; OR < 1 = lower churn odds)",
     odds_ratio_table)

# --- sklearn pipeline (predictive: stratified holdout)
# Then the predictive view: the same factors through a scikit-learn pipeline
# (one-hot encode -> logistic regression), evaluated on a held-out 20% of
# customers stratified by churn. OneHotEncoder(handle_unknown="ignore") keeps
# the pipeline safe on unseen categories at predict time.
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
show("MODEL METRICS — 20% stratified holdout", {k: round(v, 3) for k, v in metrics.items()})
show("CONFUSION MATRIX (rows = actual, cols = predicted)", pd.DataFrame(
    cm, index=["No Churn", "Churn"], columns=["No Churn", "Churn"]))

# --- robustness: model without Activation Year
# Activation Year dominates partly for a mechanical reason: recent cohorts
# have had less time to be observed churning (exposure window), not just
# better retention. Re-running without it shows how much of the model's
# apparent skill is that artifact (AUC ~0.64 vs ~0.80).
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
show("ROBUSTNESS — SAME MODEL WITHOUT ACTIVATION YEAR", {k: round(v, 3) for k, v in metrics_ny.items()})

# ---------------------------------------------------- Excel: Dashboard+Predict
# PART 4: OUTPUTS — mirror the notebook's Excel dashboard and add a
# Predictive Analytics sheet holding the most important tables.
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


# Helper: write a titled dataframe block (header row + rows) at start_row and
# return the next free row, so tables stack down the sheet.
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

show("DONE", f"Charts saved to {CHART_DIR}/ · Analysis workbook saved to {XLSX_OUT}")

# ---------------------------------------------------------------------------
# PART 5: PRESCRIPTIVE ANALYTICS — what to do about it.
# (The numbers above feed the recommendations in Churn_Analysis.pptx, slides
# 4-5. Summary of the logic:)
#
#   finding                                        -> action
#   24-month OR 0.22 vs monthly                    -> push contract migration
#                                                     at renewal (largest
#                                                     controllable lever)
#   82% of terminations = Moving Home/Going Away   -> mover's programme +
#                                                     landlord/developer
#                                                     partnerships
#   Leeds 82% / Manchester 77% churn               -> investigate local service
#                                                     quality + altnet
#                                                     overbuild pressure
#   50Mb bundle churns 82% (n=1,030)               -> entry-tier upgrade path
#   competitors not significant (p 0.13/0.72)      -> retention spend on
#                                                     contract + movers, not
#                                                     price matching
#   cohort effect mostly exposure window           -> report churn on a
#                                                     survival basis; don't
#                                                     read 2024's 37% as
#                                                     improvement
# ---------------------------------------------------------------------------
