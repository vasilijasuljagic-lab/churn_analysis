"""Build Churn_Analysis.pptx — 5-slide deck.

Slide 1: Approach & headline findings
Slide 2: Descriptive analysis — charts from the Excel dashboard
Slide 3: Predictive layer — model metrics + odds ratios
Slide 4: Prescriptive analysis — what to do about it
Slide 5: Insights, recommendations & caveats
"""
import pandas as pd
import joblib
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

NAVY = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x66, 0x66, 0x66)

df = pd.read_csv("cleaned_data.csv")
model = joblib.load("churn_model.joblib")

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide(title_text):
    s = prs.slides.add_slide(BLANK)
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = title_text
    p.font.size, p.font.bold, p.font.color.rgb = Pt(28), True, NAVY
    return s


def bullets(s, items, left=0.5, top=1.1, width=12.3, height=5.9, size=15):
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (head, body) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = head
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), True, NAVY
        if body:
            r2 = p.add_run(); r2.text = "  —  " + body
            r2.font.size, r2.font.color.rgb = Pt(size), DARK
        p.space_after = Pt(8)


def table(s, data, left, top, width, height, header=True, size=12):
    rows, cols = len(data), len(data[0])
    shape = s.shapes.add_table(rows, cols, Inches(left), Inches(top), Inches(width), Inches(height))
    t = shape.table
    for r, row in enumerate(data):
        for c, val in enumerate(row):
            cell = t.cell(r, c)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(size)
                    if header and r == 0:
                        run.font.bold = True
                        run.font.color.rgb = NAVY


def pic(s, path, left, top, width=None, height=None):
    s.shapes.add_picture(path, Inches(left), Inches(top),
                         Inches(width) if width else None,
                         Inches(height) if height else None)


# ---- Slide 1: approach & headlines
s = slide("Hyperoptic churn analysis — approach & headline findings")
bullets(s, [
    ("Data", "10,000 customers · activations 2020-01–2024-12 · terminations to 2025-09. Cleaning: Excel serial dates, '-' placeholders, no duplicates, no missing outside the two termination fields."),
    ("Churn definition", "recorded termination = Termination Date present (6,947 churned, 3,053 active → 69.5% of this base)."),
    ("Headline", "82% of terminations are 'Moving Home/Going Away' — largely structural (customer relocates off network), not dissatisfaction."),
    ("Strongest lever", "24-month contracts churn at 42.5% vs ~75% for monthly/12-month (odds 78% lower after controls)."),
    ("Geography", "Leeds 82.4% and Manchester 77.0% churn far above London 62.6% and Nottingham 41.4%."),
    ("Tools", "pandas / scikit-learn / statsmodels / Chi-square & Cramér's V / logistic regression / Flask dashboard."),
])

# ---- Slide 2: descriptive charts
s = slide("Descriptive analysis — where churn concentrates")
pic(s, "charts/nb_contract_churn.png", 0.4, 1.0, width=6.2)
pic(s, "charts/nb_city_churn.png", 6.8, 1.0, width=6.2)
pic(s, "charts/nb_cohort_churn.png", 0.4, 4.3, width=6.2)
pic(s, "charts/nb_bundle_churn_all.png", 6.8, 4.3, width=6.2)

# ---- Slide 3: predictive layer
s = slide("Predictive layer — logistic regression results")
m = model["metrics"]; mn = model["metrics_no_year"]
table(s, [
    ["Metric", "Full model", "Without activation year"],
    ["Accuracy", f"{m['accuracy']:.1%}", f"{mn['accuracy']:.1%}"],
    ["Precision", f"{m['precision']:.1%}", f"{mn['precision']:.1%}"],
    ["Recall", f"{m['recall']:.1%}", f"{mn['recall']:.1%}"],
    ["ROC-AUC", f"{m['roc_auc']:.2f}", f"{mn['roc_auc']:.2f}"],
], 0.5, 1.1, 5.6, 1.9)
ors = model["odds_ratios"]
key_terms = ["Contract Type_24 Months", "Contract Type_Monthly Rolling", "City_Manchester",
             "City_Nottingham", "Bundle Group_50Mb", "Bundle Group_Other",
             "Activation Year_2023", "Activation Year_2024"]
rows = [["Term", "Odds ratio", "p"]] + [
    [t, f"{ors.loc[t, 'Odds Ratio']:.2f}", f"{ors.loc[t, 'p-value']:.3f}"] for t in key_terms]
table(s, rows, 6.6, 1.1, 6.2, 3.2)
bullets(s, [
    ("Model", "stratified 20% holdout, one-hot encoded factors; logistic regression chosen for interpretability (odds ratios)."),
    ("Strongest signals", "contract length (24m OR 0.22 vs 12m), cohort (2024 OR 0.09 — part exposure-window effect), Manchester vs Leeds (OR 1.51), 50Mb bundle (OR 1.39)."),
    ("Not significant", "number of competitors (p = 0.13 / 0.72) and London vs Leeds (p = 0.08) carry no signal once other factors are controlled."),
    ("Caveat", "2023–24 cohort coefficients partly reflect shorter observation windows, not better retention — flagged by the no-year robustness model (AUC 0.64)."),
], top=4.5, size=12)

# ---- Slide 4: prescriptive analysis
s = slide("Prescriptive analysis — what to do about it")
bullets(s, [
    ("1. Contract migration", "move monthly/12-month customers toward 24-month terms near renewal — the single largest controllable effect (OR 0.22). Estimated addressable churn pool: ~60% of the base."),
    ("2. Mover's programme", "82% of churn is relocation. Offer seamless home-move transfers and partner with landlords/developers so 'Moving Home' doesn't mean leaving."),
    ("3. Manchester & Leeds focus", "highest churn rates and sizeable populations — investigate local service quality, installation experience and altnet overbuild pressure."),
    ("4. 50Mb entry bundle", "highest bundle churn (82%, n=1,030) — entry-tier customers may be price-sensitive or underserved; consider upgrade paths."),
    ("5. Early-tenure guardrail", "the 0–6-month group shows 100% recorded churn — an observation-window artifact, but real early churn exists (~1,070 customers); tighten onboarding and install experience."),
])

# ---- Slide 5: insights, recommendations, caveats
s = slide("Insights, recommendations & caveats")
bullets(s, [
    ("Insight", "churn in this dataset is dominated by structural movers and contract structure — price/competition play a minor recorded role (competitors V = 0.03)."),
    ("Recommendation 1", "deploy the model into CRM: score active customers (the Flask app already exposes per-profile churn probability) and trigger retention offers above a threshold."),
    ("Recommendation 2", "report churn on a survival/exposure basis — raw cohort rates overstate recent-cohort improvement."),
    ("Recommendation 3", "clarify the 'Customer not leaving' category (521 records, 7.5% of churn) — it records a termination date but ambiguous churn meaning."),
    ("Caveat", "the dataset is churn-weighted (69.5% observed churn is not the live-business rate); model AUC 0.80 is good for ranking, probabilities need recalibration on live volumes."),
])
prs.save("Churn_Analysis.pptx")
print("Saved Churn_Analysis.pptx (5 slides)")
