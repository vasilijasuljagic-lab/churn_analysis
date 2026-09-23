"""Build presentation/Churn_Analysis_Final.pptx — stakeholder deck.

Sections (business-facing order):
  1. Title — churn analysis, UK full-fibre broadband
  2. Executive summary — the answer to "why do customers leave?"
  3. Data & approach
  4. Headline findings (dashboard charts)
  5. Why customers leave — termination reasons
  6. Contract length & competition
  7. Where & what — geography
  8. Where & what — bundle
  9. When customers leave — cohort, tenure, seasonality
 10. UK fibre market context & competition
 11. Recommendations
"""
import pandas as pd
import joblib
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

NAVY = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x22, 0x22, 0x22)

model = joblib.load("churn_model.joblib")
ors = model["odds_ratios"]

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide(title_text, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = title_text
    p.font.size, p.font.bold, p.font.color.rgb = Pt(28), True, NAVY
    if subtitle:
        tb2 = s.shapes.add_textbox(Inches(0.5), Inches(0.85), Inches(12.3), Inches(0.4))
        p2 = tb2.text_frame.paragraphs[0]
        p2.text = subtitle
        p2.font.size, p2.font.italic, p2.font.color.rgb = Pt(13), True, DARK
    return s


def bullets(s, items, left=0.5, top=1.15, width=12.3, height=5.9, size=15):
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        head, body = item if isinstance(item, tuple) else (item, None)
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = "•  " + head if not head.startswith(("•", "—", "·")) else head
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bool(body), NAVY if body else DARK
        if body:
            r2 = p.add_run(); r2.text = "  —  " + body
            r2.font.size, r2.font.color.rgb = Pt(size), DARK
            r2.font.bold = False
        p.space_after = Pt(10)


def table(s, data, left, top, width, height, size=12):
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
                    if r == 0:
                        run.font.bold = True
                        run.font.color.rgb = NAVY


def pic(s, path, left, top, width=None, height=None):
    s.shapes.add_picture(path, Inches(left), Inches(top),
                         Inches(width) if width else None,
                         Inches(height) if height else None)


# ------------------------------------------------ 1. Title
s = prs.slides.add_slide(BLANK)
tb = s.shapes.add_textbox(Inches(0.9), Inches(2.2), Inches(11.5), Inches(2.2))
tf = tb.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]; p.text = "Why our customers leave"
p.font.size, p.font.bold, p.font.color.rgb = Pt(44), True, NAVY
p2 = tf.add_paragraph()
p2.text = "Churn analysis — UK full-fibre broadband · customer base of 10,000 records"
p2.font.size, p2.font.color.rgb = Pt(20), DARK
p3 = tf.add_paragraph()
p3.text = "Prepared for business stakeholders · descriptive, predictive and prescriptive analytics"
p3.font.size, p3.font.color.rgb = Pt(14), DARK

# ------------------------------------------------ 2. Executive summary
s = slide("Executive summary — why customers leave")
bullets(s, [
    ("The answer in one line", "most churn is structural, not dissatisfaction: 82% of terminations are customers moving home or leaving the area — where our network may not reach."),
    ("Recorded churn", "6,947 of 10,000 customers (69.5%) terminated; the base is churn-weighted, so treat rates as relative comparisons, not the live-business rate."),
    ("The strongest lever is contract structure", "24-month contracts churn at 42.5% vs ~75% for monthly/12-month — 78% lower odds of churn after controls."),
    ("Geography matters", "Leeds (82%) and Manchester (77%) churn well above London (63%) and Nottingham (41%)."),
    ("Competition is NOT the driver", "number of competitors present has no significant effect once other factors are controlled — retention spend should target contract terms and movers, not price matching."),
    ("What to do", "contract migration at renewal, a mover's programme, and Manchester/Leeds service-quality review — recommendations on the last slide."),
], size=15)

# ------------------------------------------------ 3. Data & approach
s = slide("Data & approach")
bullets(s, [
    ("Data", "10,000 customers · activations Jan 2020 – Dec 2024 · terminations recorded to Sep 2025. Fields: city, postcode, bundle, contract duration, competitors, activation/termination dates and reason."),
    ("Cleaning", "Excel serial dates parsed, '-' placeholders → missing, no duplicates; only missing fields are termination-related — missing termination = still active, i.e. meaningful, not lost data."),
    ("Churn definition", "a record with a termination date counts as churned (6,947 churned / 3,053 active)."),
    ("Analytics flow", "descriptive (where churn concentrates) → statistics (chi-square, Cramér's V, correlations) → predictive (logistic regression, odds ratios + holdout evaluation) → prescriptive (recommendations)."),
    ("Model", "logistic regression on contract type, city, bundle group, competitors, activation year — chosen for interpretability: holdout accuracy 78%, AUC 0.80, recall 89%."),
])

# ------------------------------------------------ 4. Headline findings
s = slide("Headline findings — where churn concentrates")
pic(s, "charts/nb_contract_churn.png", 0.4, 1.0, width=6.2)
pic(s, "charts/nb_city_churn.png", 6.8, 1.0, width=6.2)
pic(s, "charts/nb_bundle_churn_all.png", 0.4, 4.25, width=6.2)
pic(s, "charts/nb_cohort_churn.png", 6.8, 4.25, width=6.2)

# ------------------------------------------------ 5. Why customers leave
s = slide("Why customers leave — termination reasons")
pic(s, "charts/termination_reasons.png", 0.4, 1.1, width=7.6)
bullets(s, [
    ("Moving Home/Going Away", "82.1% of all terminations (5,701 customers) — largely structural: the customer relocates, not necessarily dissatisfied."),
    ("'Customer not leaving'", "7.5% of churn records (521) — ambiguous category; its profile matches the overall base, kept but flagged."),
    ("Bad Debt", "5.5% — a collections/pricing-design issue more than a service issue."),
    ("Complaint + Package/Deal/Cost", "under 2% combined — classic service/price churn is a small share."),
], left=8.2, top=1.2, width=4.7, size=13)

# ------------------------------------------------ 6. Contract length & competition
s = slide("Contract length & competition")
pic(s, "charts/nb_contract_churn.png", 0.4, 1.1, width=6.4)
key = [["Term", "OR", "sig."],
       ["24 Months (vs 12m)", f"{ors.loc['Contract Type_24 Months','Odds Ratio']:.2f}", "***"],
       ["Monthly (vs 12m)", f"{ors.loc['Contract Type_Monthly Rolling','Odds Ratio']:.2f}", "***"],
       ["1 competitor", f"{ors.loc['Number of Competitors_1','Odds Ratio']:.2f}", "n.s."],
       ["2 competitors", f"{ors.loc['Number of Competitors_2','Odds Ratio']:.2f}", "n.s."]]
table(s, key, 7.2, 1.3, 5.6, 1.7)
bullets(s, [
    ("Contract is the biggest controllable lever", "24-month customers have ~78% lower odds of churning than 12-month; monthly-rolling churns more (+28%)."),
    ("Competition is not significant", "having 1 or 2 competitors in the area does not move churn odds (p = 0.13 / 0.72) — presence of rivals alone doesn't drive exits."),
    ("But", "part of the 24-month gap is mechanical (still in-contract) — it's a lever, not pure satisfaction."),
], left=7.2, top=3.2, width=5.6, size=12)

# ------------------------------------------------ 7. Geography
s = slide("Where — geography")
pic(s, "charts/nb_city_churn.png", 0.4, 1.1, width=6.6)
key = [["City (vs Leeds)", "OR", "sig."],
       ["London", f"{ors.loc['City_London','Odds Ratio']:.2f}", "p=.08"],
       ["Manchester", f"{ors.loc['City_Manchester','Odds Ratio']:.2f}", "***"],
       ["Nottingham", f"{ors.loc['City_Nottingham','Odds Ratio']:.2f}", "***"]]
table(s, key, 7.4, 1.3, 5.4, 1.5)
bullets(s, [
    ("Manchester", "churns ~51% more than Leeds after controls — the strongest geography signal."),
    ("Nottingham", "churns ~64% less — smallest base (n=152) but consistent."),
    ("Action", "review service quality, install experience and altnet overbuild pressure in Manchester and Leeds."),
], left=7.4, top=3.1, width=5.4, size=12)

# ------------------------------------------------ 8. Bundle
s = slide("What — bundle")
pic(s, "charts/nb_bundle_churn_all.png", 0.4, 1.1, width=7.2)
bullets(s, [
    ("50Mb entry tier churns most", "82.0% (n=1,030; OR 1.39 vs 150Mb) — price-sensitive or underserved entry customers."),
    ("Mid/high tiers churn less", "500Mb 67%, 1Gb 66%; 'Other' niche bundles show the lowest recorded churn (small n)."),
    ("Action", "an upgrade path for the entry tier is cheaper than acquiring replacements."),
], left=7.8, top=1.3, width=5.0, size=13)

# ------------------------------------------------ 9. When customers leave
s = slide("When customers leave — timing")
pic(s, "charts/nb_monthly_churn.png", 0.4, 1.0, width=6.4)
pic(s, "charts/nb_tenure_hist.png", 6.9, 1.0, width=6.2)
bullets(s, [
    ("Churn concentrates around contract end", "median churned tenure ≈ 12 months; the <6-month bands showing 100% are an observation artifact (active customers can't yet appear there) — though ~1,070 real early churners still warrant onboarding attention."),
    ("Cohort rates reflect exposure", "2024's 37% is mostly less time to churn, not better retention — report on a survival basis."),
    ("Same-day terminations", "28 customers left on activation day — worth an order-flow check."),
], top=4.5, size=13)

# ------------------------------------------------ 10. UK market context
s = slide("UK fibre market context — why this matters")
bullets(s, [
    ("Altnet overbuild", "the UK altnet sector (incl. Hyperoptic) grew fast, often overbuilding the same dense postcodes — when a mover's new address sits on another network, churn is automatic, not competitive loss."),
    ("Price pressure", "wholesale FTTP prices fell ~40% in real terms over the build-out period — retention via contract length beats price wars."),
    ("Consolidation wave", "altnets are consolidating (debt-funded build-out + missed take-up targets); keeping existing customers is far cheaper than the market's rising acquisition costs."),
    ("Read on our data", "competitor count not being significant + mover-dominated reasons support the structural view: the fight is coverage and contracts, not head-to-head pricing."),
], size=15)

# ------------------------------------------------ 11. Recommendations
s = slide("Recommendations — prescriptive")
bullets(s, [
    ("1. Contract migration", "move monthly/12-month customers to 24-month terms at renewal — biggest controllable effect (OR 0.22)."),
    ("2. Mover's programme", "82% of churn is relocation: seamless home-move transfers + landlord/developer partnerships keep movers on-network."),
    ("3. Manchester & Leeds review", "highest churn rates — local service quality, install experience, overbuild pressure."),
    ("4. Entry-tier upgrade path", "50Mb bundle churns most (82%) — nudge toward higher tiers."),
    ("5. Deploy the model", "score active customers in CRM (dashboard calculator already live) and trigger offers above a risk threshold."),
    ("6. Better churn reporting", "report survival/exposure-based churn; clarify the 'Customer not leaving' category."),
], size=15)

prs.save("presentation/Churn_Analysis_Final.pptx")
print("Saved presentation/Churn_Analysis_Final.pptx")
