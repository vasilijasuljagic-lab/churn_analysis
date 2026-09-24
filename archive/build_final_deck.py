"""Build presentation/Churn_Analysis_Final.pptx — stakeholder deck (5 slides).

  1. Title + executive summary — the answer to "why do customers leave?"
  2. Data & approach + headline findings (charts)
  3. Why customers leave — termination reasons + contract length & competition
  4. Where & what & when — geography, bundle, churn timing
  5. UK fibre market context + prescriptive recommendations
"""
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


def bullets(s, items, left=0.5, top=1.15, width=12.3, height=5.9, size=14):
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
        p.space_after = Pt(9)


def table(s, data, left, top, width, height, size=11):
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


# --------------------------------------------- 1. Title + exec summary
s = slide("Why our customers leave",
          "Churn analysis · UK full-fibre broadband · 10,000 customer records · descriptive → predictive → prescriptive")
bullets(s, [
    ("The answer in one line", "most churn is structural, not dissatisfaction: 82% of terminations are customers moving home or leaving the area — where our network may not reach."),
    ("Recorded churn", "6,947 of 10,000 customers (69.5%) terminated; the base is churn-weighted, so treat rates as relative comparisons, not the live-business rate."),
    ("Strongest controllable lever", "24-month contracts churn at 42.5% vs ~75% for monthly/12-month — 78% lower odds of churn after controls."),
    ("Geography", "Leeds (82%) and Manchester (77%) churn well above London (63%) and Nottingham (41%)."),
    ("Competition is NOT the driver", "number of competitors has no significant effect once other factors are controlled — spend on contract terms and movers, not price matching."),
    ("What to do", "contract migration at renewal, a mover's programme, and a Manchester/Leeds service-quality review — recommendations on the last slide."),
], top=1.5, size=15)

# --------------------------------------------- 2. Data & approach + findings
s = slide("Data, approach & headline findings")
bullets(s, [
    ("Data", "10,000 customers · activations Jan 2020 – Dec 2024 · terminations to Sep 2025. Cleaning: serial dates parsed, '-' → missing; only termination fields are missing — missing termination = still active."),
    ("Approach", "descriptive → statistics (chi-square, Cramér's V, correlations) → logistic regression (interpretable odds ratios; holdout acc 78%, AUC 0.80, recall 89%)."),
], top=1.0, height=1.6, size=12)
pic(s, "charts/nb_contract_churn.png", 0.3, 2.7, width=6.2)
pic(s, "charts/nb_city_churn.png", 6.8, 2.7, width=6.2)
pic(s, "charts/nb_bundle_churn_all.png", 0.3, 5.35, width=6.2, height=None)
pic(s, "charts/nb_cohort_churn.png", 6.8, 5.35, width=6.2, height=None)

# --------------------------------------------- 3. Why + contract & competition
s = slide("Why customers leave — reasons, contract & competition")
pic(s, "charts/termination_reasons.png", 0.3, 1.1, width=6.9)
key = [["Term", "OR", "sig."],
       ["24 Months (vs 12m)", f"{ors.loc['Contract Type_24 Months','Odds Ratio']:.2f}", "***"],
       ["Monthly (vs 12m)", f"{ors.loc['Contract Type_Monthly Rolling','Odds Ratio']:.2f}", "***"],
       ["1 competitor", f"{ors.loc['Number of Competitors_1','Odds Ratio']:.2f}", "n.s."],
       ["2 competitors", f"{ors.loc['Number of Competitors_2','Odds Ratio']:.2f}", "n.s."]]
table(s, key, 7.5, 1.15, 5.2, 1.6)
bullets(s, [
    ("Moving Home/Going Away = 82%", "5,701 customers — structural churn, not dissatisfaction; 'Customer not leaving' (7.5%) is ambiguous but profile-matched to the base; Complaint + Package/Deal/Cost < 2%."),
    ("Contract is the biggest lever", "24-month = 78% lower churn odds vs 12-month; monthly rolling +28%. Part of the gap is mechanical (still in-contract)."),
    ("Competitors don't move churn", "1 or 2 rivals present: no significant effect (p = 0.13 / 0.72)."),
], left=7.5, top=3.0, width=5.4, size=12)

# --------------------------------------------- 4. Where / what / when
s = slide("Where, what & when — geography, bundle, timing")
pic(s, "charts/nb_city_churn.png", 0.3, 1.0, width=4.3, height=2.6)
pic(s, "charts/nb_bundle_churn_all.png", 4.7, 1.0, width=4.3, height=2.6)
pic(s, "charts/nb_monthly_churn.png", 9.1, 1.0, width=4.1, height=2.6)
bullets(s, [
    ("Where", "Manchester churns ~51% more than Leeds after controls (OR 1.51); Nottingham ~64% less (OR 0.36). Leeds 82% / Manchester 77% vs London 63% / Nottingham 41%."),
    ("What", "50Mb entry tier churns most — 82% (n=1,030; OR 1.39 vs 150Mb). Mid/high tiers lower: 500Mb 67%, 1Gb 66%."),
    ("When", "churn concentrates around contract end — median churned tenure ≈ 12 months. <6-month bands show 100% (observation artifact) but ~1,070 real early churners warrant onboarding review; 28 same-day terminations; 2024's 37% cohort rate is mostly less time to churn — report on a survival basis."),
], top=4.2, size=13)

# --------------------------------------------- 5. Market context + recommendations
s = slide("UK fibre market context & recommendations")
bullets(s, [
    ("Altnet overbuild", "47% of the UK now has more than one FTTP network (Cartesian); altnets report overbuild by other altnets as a sharply rising challenge (INCA). When a mover's new address sits on another network, churn is automatic, not competitive loss — matching our data: mover-dominated reasons + competitors not significant."),
    ("Price pressure & consolidation", "entry-level altnet FTTP prices fell £22 → £19 (2020–25), well below BT's £35 (INCA); Cartesian calls pricing 'very aggressive' and consolidation needed for economies of scale — retaining customers beats rising acquisition costs."),
    ("1. Contract migration", "move monthly/12-month customers to 24-month terms at renewal (OR 0.22 — biggest controllable effect)."),
    ("2. Mover's programme", "seamless home-move transfers + landlord/developer partnerships for the 82% who relocate."),
    ("3. Manchester & Leeds review", "local service quality, install experience, overbuild pressure."),
    ("4. Entry-tier upgrade path", "50Mb churns most (82%) — nudge toward higher tiers; deploy the model in CRM to score active customers; report churn on a survival basis."),
], top=1.0, height=5.6, size=12)

# sources footnote (small, bottom of slide)
tb = s.shapes.add_textbox(Inches(0.5), Inches(6.75), Inches(12.4), Inches(0.7))
tf = tb.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]
p.text = ("Sources: Cartesian, 'The State of UK Fibre' (2025) — cartesian.com/state-of-uk-fibre · "
          "INCA & Point Topic, 'State of the Altnets' annual report — inca.coop · "
          "Ofcom, Telecoms Access Review / copper switchover proposals · "
          "Internal dataset: Case_Study_Data_1.xlsx (10,000 customers).")
p.font.size, p.font.color.rgb = Pt(9), RGBColor(0x80, 0x80, 0x80)

prs.save("presentation/Churn_Analysis_Final.pptx")
print("Saved presentation/Churn_Analysis_Final.pptx")
