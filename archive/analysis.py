"""Churn analysis for Case_Study_Data_1.xlsx.

Cleans the dataset, derives churn flags/tenure, computes segment churn rates,
and saves charts to charts/ plus a summary CSV set for the slide deck.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

OUT = "charts"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 11})

EPOCH = pd.Timestamp("1899-12-30")
df = pd.read_excel("Case_Study_Data_1.xlsx", sheet_name="Case Study Data")

# --- Cleaning ---------------------------------------------------------------
df.columns = [c.strip() for c in df.columns]
df["Termination Reason"] = df["Termination Reason"].fillna("-").astype(str).str.strip()

df["Activation Date"] = EPOCH + pd.to_timedelta(pd.to_numeric(df["Activation Date"], errors="coerce"), unit="D")
term_num = pd.to_numeric(df["Termination Date"], errors="coerce")
df["Termination Date"] = EPOCH + pd.to_timedelta(term_num, unit="D")

# '-' termination reason and non-numeric termination date => still active
df["Churned"] = df["Termination Date"].notna() & (df["Termination Reason"] != "-")
SNAPSHOT = pd.Timestamp("2025-09-01")
df["End Date"] = df["Termination Date"].fillna(SNAPSHOT)
df["Tenure Days"] = (df["End Date"] - df["Activation Date"]).dt.days.clip(lower=0)
df["Tenure Months"] = df["Tenure Days"] / 30.44
df["Activation Year"] = df["Activation Date"].dt.year
df["Term YearMonth"] = df["Termination Date"].dt.to_period("M")

df["Contract"] = df["Contract Duration"].map({0: "Monthly rolling", 12: "12-month", 24: "24-month"})
df["Speed"] = df["Bundle"]

print("Rows:", len(df), "| Churned:", df["Churned"].sum(), "| Churn rate:", round(df["Churned"].mean() * 100, 1), "%")
print("Active:", (~df["Churned"]).sum())


def churn_by(col, order=None):
    g = df.groupby(col)["Churned"].agg(["mean", "count"])
    g["mean"] = (g["mean"] * 100).round(1)
    if order:
        g = g.reindex(order)
    return g


# --- Segment tables ----------------------------------------------------------
for col in ["City", "Contract", "Speed", "Number of Competitors"]:
    print("\n== churn by", col)
    print(churn_by(col).sort_values("mean", ascending=False))

print("\n== Termination reasons (churned only)")
reasons = df.loc[df["Churned"], "Termination Reason"].value_counts()
print(reasons)
print("\nTop reasons % of churn:")
print((reasons / reasons.sum() * 100).round(1).head(8))

# --- Charts ------------------------------------------------------------------
BLUE, GREY, RED = "#1f4e79", "#9aa5b1", "#c0392b"

# 1 churn by contract
order = ["Monthly rolling", "12-month", "24-month"]
g = churn_by("Contract", order)
fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(g.index, g["mean"], color=[RED, BLUE, BLUE])
for b, (m, c) in zip(bars, zip(g["mean"], g["count"])):
    ax.text(b.get_x() + b.get_width() / 2, m + 1, f"{m}%\n(n={c})", ha="center", fontsize=9)
ax.set_ylabel("Churn rate (%)"); ax.set_title("Churn rate by contract duration"); ax.set_ylim(0, g["mean"].max() * 1.25)
fig.tight_layout(); fig.savefig(f"{OUT}/churn_by_contract.png"); plt.close(fig)

# 2 churn by city
g = churn_by("City").sort_values("mean")
fig, ax = plt.subplots(figsize=(6, 4))
ax.barh(g.index, g["mean"], color=BLUE)
for i, (m, c) in enumerate(zip(g["mean"], g["count"])):
    ax.text(m + 0.5, i, f"{m}% (n={c})", va="center", fontsize=9)
ax.set_xlabel("Churn rate (%)"); ax.set_title("Churn rate by city")
fig.tight_layout(); fig.savefig(f"{OUT}/churn_by_city.png"); plt.close(fig)

# 3 churn by speed (top bundles, n>=50)
speed_order = ["30Mb", "50Mb", "100/10Mb", "100/20Mb", "150Mb", "250Mb", "500Mb", "750Mb", "1Gb"]
g = churn_by("Speed", speed_order).dropna()
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(g.index, g["mean"], color=BLUE)
for i, (m, c) in enumerate(zip(g["mean"], g["count"])):
    ax.text(i, m + 1, f"{m}%", ha="center", fontsize=9)
ax.set_ylabel("Churn rate (%)"); ax.set_title("Churn rate by bundle speed")
plt.xticks(rotation=30)
fig.tight_layout(); fig.savefig(f"{OUT}/churn_by_bundle.png"); plt.close(fig)

# 4 churn by competitors
g = churn_by("Number of Competitors")
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(g.index.astype(str), g["mean"], color=BLUE)
for i, (m, c) in enumerate(zip(g["mean"], g["count"])):
    ax.text(i, m + 1, f"{m}%\n(n={c})", ha="center", fontsize=9)
ax.set_xlabel("Competitors at location"); ax.set_ylabel("Churn rate (%)")
ax.set_title("Churn rate by competitor presence"); ax.set_ylim(0, g["mean"].max() * 1.3)
fig.tight_layout(); fig.savefig(f"{OUT}/churn_by_competitors.png"); plt.close(fig)

# 5 termination reasons (churned, top 8)
top = reasons.head(8)[::-1]
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.barh(top.index, top.values, color=BLUE)
for i, v in enumerate(top.values):
    ax.text(v + 20, i, str(v), va="center", fontsize=9)
ax.set_title("Termination reasons (churned customers)")
fig.tight_layout(); fig.savefig(f"{OUT}/termination_reasons.png"); plt.close(fig)

# 6 tenure distribution churned vs active
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.hist(df.loc[df["Churned"], "Tenure Months"], bins=40, alpha=0.7, label="Churned", color=RED)
ax.hist(df.loc[~df["Churned"], "Tenure Months"], bins=40, alpha=0.7, label="Active", color=GREY)
ax.set_xlabel("Tenure (months)"); ax.set_ylabel("Customers"); ax.legend()
ax.set_title("Customer tenure: churned vs active")
fig.tight_layout(); fig.savefig(f"{OUT}/tenure_hist.png"); plt.close(fig)

# 7 monthly churn volume + activation cohort churn rate by year
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
t = df.loc[df["Churned"]].groupby("Term YearMonth").size()
t.index = t.index.to_timestamp()
axes[0].plot(t.index, t.values, color=RED)
axes[0].set_title("Churn events per month"); axes[0].set_ylabel("Churned customers")
g = churn_by("Activation Year")
axes[1].bar(g.index.astype(str), g["mean"], color=BLUE)
axes[1].set_title("Churn rate by activation cohort"); axes[1].set_ylabel("Churn rate (%)")
for i, m in enumerate(g["mean"]):
    axes[1].text(i, m + 1, f"{m}%", ha="center", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/churn_time.png"); plt.close(fig)

# churned median tenure, early churn (<=3 months)
ch = df[df["Churned"]]
print("\nMedian tenure churned (months):", round(ch["Tenure Months"].median(), 1))
print("Active median tenure (months):", round(df.loc[~df["Churned"], "Tenure Months"].median(), 1))
print("Churned within 3 months:", (ch["Tenure Months"] <= 3).sum(), f"({(ch['Tenure Months'] <= 3).mean() * 100:.1f}% of churn)")

df.to_csv("cleaned_data.csv", index=False)
print("\nSaved cleaned_data.csv and", len(os.listdir(OUT)), "charts to", OUT)
