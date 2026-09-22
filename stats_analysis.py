"""Statistical analysis of churn: descriptives, association/correlation tests
and a predictive model on cohort, city, geography (postcode district),
contract type and number of competitors.

Inputs : cleaned_data.csv (from analysis.py)
Outputs: stats_report.md, charts/stats_*.png, churn_model.joblib
"""
import warnings
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, brier_score_loss, accuracy_score,
                             roc_curve, classification_report)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 150, "font.size": 10})
BLUE, RED = "#1f4e79", "#c0392b"

FEATURES = ["Cohort", "City", "District", "Contract", "Competitors"]
report = []


def h(t, lvl=2):
    report.append(f"\n{'#' * lvl} {t}\n")


def md(df, floatfmt=".3f"):
    report.append(df.to_markdown(floatfmt=floatfmt) + "\n")


# --------------------------------------------------------------------------
# 1. Load & feature engineering
# --------------------------------------------------------------------------
df = pd.read_csv("cleaned_data.csv", parse_dates=["Activation Date", "Termination Date"])
df["Churned"] = df["Churned"].astype(int)
df["Cohort"] = df["Activation Year"].astype(int)
df["District"] = df["Postcode"].astype(str).str.strip().str.upper().str.split().str[0]
df["Contract"] = df["Contract Duration"].map({0: "Monthly", 12: "12-month", 24: "24-month"})
df["Competitors"] = df["Number of Competitors"].astype(int)
df["Has Competitor"] = (df["Competitors"] > 0).astype(int)
df["Months Since Activation"] = (pd.Timestamp("2025-09-01") - df["Activation Date"]).dt.days / 30.44

report.append("# Churn Statistical Analysis\n")
report.append(f"Dataset: {len(df):,} customers, {df['Churned'].sum():,} churned "
              f"({df['Churned'].mean():.1%}).\n")

# --------------------------------------------------------------------------
# 2. Descriptive statistics
# --------------------------------------------------------------------------
h("1. Descriptive statistics")
num = df[["Contract Duration", "Competitors", "Tenure Months", "Months Since Activation", "Churned"]]
md(num.describe().T)

h("Churn rate by factor (with 95% Wilson CI)", 3)
rows = []
for f in FEATURES:
    g = df.groupby(f)["Churned"].agg(["sum", "count", "mean"])
    for k, r in g.iterrows():
        lo, hi = sm.stats.proportion_confint(r["sum"], r["count"], method="wilson")
        rows.append([f, k, int(r["count"]), r["mean"], lo, hi])
ci = pd.DataFrame(rows, columns=["Factor", "Level", "n", "Churn rate", "CI low", "CI high"])
md(ci.set_index(["Factor", "Level"]))

# --------------------------------------------------------------------------
# 3. Correlation / association analysis
# --------------------------------------------------------------------------
h("2. Correlation and association analysis")
report.append(
    "Method selection:\n"
    "- **Point-biserial** (mathematically identical to Pearson with a 0/1 variable) for *churn (binary)* vs "
    "numeric/ordinal predictors: contract duration, number of competitors, cohort year, months since activation.\n"
    "- **Phi coefficient** for binary vs binary (churn vs has-competitor).\n"
    "- **Chi-square + Cramér's V** for churn vs *nominal* factors (city, postcode district, contract type, bundle).\n"
    "- **Pearson** only between two numeric/ordinal predictors (with Spearman as a rank-based robustness check).\n"
    "- Tenure is excluded from predictors: it is only observed at termination and is therefore a *consequence* "
    "of churn (leakage), not a driver.\n")

h("2a. Point-biserial correlations: churn vs numeric predictors", 3)
rows = []
for c in ["Contract Duration", "Competitors", "Cohort", "Months Since Activation"]:
    r, p = stats.pointbiserialr(df["Churned"], df[c])
    rows.append([c, r, p, "point-biserial"])
r, p = stats.pearsonr(df["Churned"], df["Has Competitor"])
rows.append(["Has Competitor (0/1)", r, p, "phi"])
pb = pd.DataFrame(rows, columns=["Predictor", "r", "p-value", "Method"]).set_index("Predictor")
md(pb, ".4f")

h("2b. Chi-square tests and Cramér's V: churn vs categorical factors", 3)


def cramers_v(x, y):
    ct = pd.crosstab(x, y)
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    n = ct.values.sum()
    v = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
    return chi2, p, dof, v


rows = []
for c in ["City", "District", "Contract", "Cohort", "Competitors", "Bundle"]:
    chi2, p, dof, v = cramers_v(df[c], df["Churned"])
    rows.append([c, chi2, dof, p, v])
cv = pd.DataFrame(rows, columns=["Factor", "chi2", "dof", "p-value", "Cramér's V"]).set_index("Factor")
md(cv.sort_values("Cramér's V", ascending=False), ".4f")

h("2c. Pearson / Spearman among numeric predictors", 3)
numeric = df[["Contract Duration", "Competitors", "Cohort", "Months Since Activation"]]
pear = numeric.corr(method="pearson")
spear = numeric.corr(method="spearman")
report.append("Pearson:\n"); md(pear)
report.append("Spearman:\n"); md(spear)

# correlation heatmap
full = df[["Churned", "Contract Duration", "Competitors", "Cohort", "Months Since Activation"]]
corr = full.corr()
fig, ax = plt.subplots(figsize=(6.5, 5))
im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr))); ax.set_yticks(range(len(corr)))
ax.set_xticklabels(corr.columns, rotation=35, ha="right"); ax.set_yticklabels(corr.columns)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=9)
fig.colorbar(im); ax.set_title("Correlation matrix (point-biserial for Churned row/col)")
fig.tight_layout(); fig.savefig("charts/stats_corr_heatmap.png"); plt.close(fig)

# Cramér's V bar
fig, ax = plt.subplots(figsize=(6.5, 4))
cvs = cv["Cramér's V"].sort_values()
ax.barh(cvs.index, cvs.values, color=BLUE)
for i, v in enumerate(cvs.values):
    ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=9)
ax.set_xlabel("Cramér's V (association with churn)"); ax.set_title("Strength of association with churn")
fig.tight_layout(); fig.savefig("charts/stats_cramers_v.png"); plt.close(fig)

# --------------------------------------------------------------------------
# 4. Explanatory logistic regression (odds ratios)
# --------------------------------------------------------------------------
h("3. Logistic regression (explanatory) — odds ratios")
report.append("Reference levels: Cohort 2020, City London, Contract Monthly, Competitors 0. "
              "District is nested within City, so a separate district-only model is shown.\n")
logit = smf.logit("Churned ~ C(Cohort) + C(City) + C(Contract, Treatment('Monthly')) + C(Competitors)",
                  data=df).fit(disp=0)
ors = pd.DataFrame({"Odds ratio": np.exp(logit.params), "CI low": np.exp(logit.conf_int()[0]),
                    "CI high": np.exp(logit.conf_int()[1]), "p-value": logit.pvalues})
ors.index = (ors.index.str.replace("C(Contract, Treatment('Monthly'))", "Contract", regex=False)
             .str.replace("C(", "", regex=False).str.replace(")", "", regex=False))
md(ors, ".3f")
report.append(f"Pseudo R² (McFadden): {logit.prsquared:.3f}; LLR p-value: {logit.llr_pvalue:.2e}\n")

logit_d = smf.logit("Churned ~ C(Cohort) + C(District, Treatment('E14')) + C(Contract, Treatment('Monthly')) + C(Competitors)",
                    data=df).fit(disp=0)
ors_d = pd.DataFrame({"Odds ratio": np.exp(logit_d.params), "p-value": logit_d.pvalues})
ors_d = ors_d[ors_d.index.str.contains("District")]
ors_d.index = ors_d.index.str.extract(r"\[T\.(.+)\]")[0].values
small = df["District"].value_counts()
ors_d = ors_d[ors_d.index.map(lambda d: small[d] >= 20)]
h("District odds ratios (reference E14, London; districts with n<20 omitted)", 3)
md(ors_d.sort_values("Odds ratio"), ".3f")

# odds ratio plot
plot_or = ors.drop("Intercept")
fig, ax = plt.subplots(figsize=(7, 5))
y = range(len(plot_or))
ax.errorbar(plot_or["Odds ratio"], y, xerr=[plot_or["Odds ratio"] - plot_or["CI low"],
            plot_or["CI high"] - plot_or["Odds ratio"]], fmt="o", color=BLUE, capsize=3)
ax.axvline(1, color="grey", ls="--")
ax.set_yticks(list(y)); ax.set_yticklabels(plot_or.index); ax.set_xscale("log")
ax.set_xlabel("Odds ratio (log scale, 95% CI)"); ax.set_title("Churn odds ratios — logistic regression")
fig.tight_layout(); fig.savefig("charts/stats_odds_ratios.png"); plt.close(fig)

# --------------------------------------------------------------------------
# 5. Predictive modelling
# --------------------------------------------------------------------------
h("4. Predictive modelling")
X = df[FEATURES].copy()
X["Cohort"] = X["Cohort"].astype(str)
X["Competitors"] = X["Competitors"].astype(str)
y = df["Churned"]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)

pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES)])
models = {
    "Logistic regression": Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000, C=1.0))]),
    "Gradient boosting": Pipeline([("pre", pre), ("clf", GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=3, random_state=42))]),
}
cvk = StratifiedKFold(5, shuffle=True, random_state=42)
rows, fitted = [], {}
fig, ax = plt.subplots(figsize=(5.5, 5))
for name, m in models.items():
    cv_auc = cross_val_score(m, X_tr, y_tr, cv=cvk, scoring="roc_auc")
    m.fit(X_tr, y_tr)
    proba = m.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    rows.append([name, cv_auc.mean(), cv_auc.std(), roc_auc_score(y_te, proba),
                 accuracy_score(y_te, pred), brier_score_loss(y_te, proba)])
    fpr, tpr, _ = roc_curve(y_te, proba)
    ax.plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y_te, proba):.3f})")
    fitted[name] = m
ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
ax.set_title("ROC — hold-out test set"); ax.legend(loc="lower right")
fig.tight_layout(); fig.savefig("charts/stats_roc.png"); plt.close(fig)

perf = pd.DataFrame(rows, columns=["Model", "CV AUC mean", "CV AUC sd", "Test AUC", "Test accuracy", "Brier"]).set_index("Model")
md(perf)
base = y_te.mean()
report.append(f"Baseline (predict majority class) accuracy: {max(base, 1 - base):.3f}. "
              f"Baseline Brier: {base * (1 - base):.3f}.\n")

best_name = perf["Test AUC"].idxmax()
best = fitted[best_name]
report.append(f"Selected model: **{best_name}**.\n\n```\n"
              + classification_report(y_te, (best.predict_proba(X_te)[:, 1] >= 0.5).astype(int),
                                      target_names=["Active", "Churned"]) + "```\n")

# Feature importance (permutation on hold-out, grouped by original factor)
from sklearn.inspection import permutation_importance
pi = permutation_importance(best, X_te, y_te, scoring="roc_auc", n_repeats=10, random_state=42)
imp = pd.DataFrame({"Factor": FEATURES, "AUC drop (mean)": pi.importances_mean,
                    "sd": pi.importances_std}).set_index("Factor").sort_values("AUC drop (mean)", ascending=False)
h("Permutation importance (drop in hold-out AUC when factor is shuffled)", 3)
md(imp, ".4f")
fig, ax = plt.subplots(figsize=(6, 3.8))
ax.barh(imp.index[::-1], imp["AUC drop (mean)"][::-1], xerr=imp["sd"][::-1], color=BLUE, capsize=3)
ax.set_xlabel("Mean AUC decrease"); ax.set_title(f"Permutation importance — {best_name}")
fig.tight_layout(); fig.savefig("charts/stats_importance.png"); plt.close(fig)

# Calibration
h("Calibration (deciles of predicted probability)", 3)
proba = best.predict_proba(X_te)[:, 1]
cal = pd.DataFrame({"pred": proba, "obs": y_te.values})
cal["decile"] = pd.qcut(cal["pred"], 10, labels=False, duplicates="drop")
calt = cal.groupby("decile").agg(predicted=("pred", "mean"), observed=("obs", "mean"), n=("obs", "size"))
md(calt)
fig, ax = plt.subplots(figsize=(5, 5))
ax.plot(calt["predicted"], calt["observed"], "o-", color=BLUE); ax.plot([0, 1], [0, 1], "k--", lw=0.8)
ax.set_xlabel("Predicted churn probability"); ax.set_ylabel("Observed churn rate"); ax.set_title("Calibration")
fig.tight_layout(); fig.savefig("charts/stats_calibration.png"); plt.close(fig)

# --------------------------------------------------------------------------
# 6. Scenario table for the future app & model persistence
# --------------------------------------------------------------------------
h("5. Example scenario predictions (selected model)")
scen = pd.DataFrame([
    ["2024", "London", "E14", "24-month", "1"],
    ["2024", "London", "E14", "Monthly", "1"],
    ["2023", "Manchester", "M15", "12-month", "1"],
    ["2022", "Leeds", "LS9", "Monthly", "1"],
    ["2021", "Nottingham", "NG1", "24-month", "0"],
    ["2020", "London", "SW11", "12-month", "0"],
], columns=FEATURES)
scen["P(churn)"] = best.predict_proba(scen)[:, 1]
md(scen.set_index(FEATURES))

final = Pipeline(best.steps)  # refit on all data for deployment
final.fit(X, y)
levels = {f: sorted(X[f].unique().tolist()) for f in FEATURES}
levels["District by City"] = {c: sorted(df.loc[df["City"] == c, "District"].unique().tolist())
                              for c in levels["City"]}
joblib.dump({"model": final, "features": FEATURES, "levels": levels, "model_name": best_name,
             "base_rate": float(y.mean())}, "churn_model.joblib")

h("6. Notes for the churn-calculator app")
report.append(
    "- `churn_model.joblib` holds a dict: `model` (sklearn Pipeline, expects a DataFrame with columns "
    f"{FEATURES}; all values as strings), `levels` (valid values per factor incl. `District by City`), "
    "`base_rate`.\n"
    "- Call `predict_churn(cohort, city, district, contract, competitors)` in `churn_model.py` to get a probability.\n"
    "- Probabilities reflect this churn-weighted sample (base rate ~69%); for a live base, recalibrate "
    "the intercept to the true churn rate.\n"
    "- Recent cohorts (2024) have had less exposure time; cohort captures both vintage and censoring effects.\n")

with open("stats_report.md", "w") as f:
    f.write("\n".join(report))
print("\n".join(report))
print("\nSaved stats_report.md, churn_model.joblib and charts/stats_*.png")
