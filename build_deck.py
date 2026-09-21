"""Builds Churn_Analysis.pptx from charts/ produced by analysis.py."""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

NAVY = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x22, 0x22, 0x22)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide(title, subtitle=None):
    s = prs.slides.add_slide(BLANK)
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.9))
    p = tb.text_frame.paragraphs[0]
    p.text = title
    p.font.size = Pt(30); p.font.bold = True; p.font.color.rgb = NAVY
    if subtitle:
        st = s.shapes.add_textbox(Inches(0.5), Inches(1.05), Inches(12.3), Inches(0.5))
        q = st.text_frame.paragraphs[0]
        q.text = subtitle
        q.font.size = Pt(15); q.font.color.rgb = DARK
    return s


def bullets(s, items, left=0.6, top=1.6, width=12.1, height=5.4, size=18):
    tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame; tf.word_wrap = True
    for i, (lvl, txt, bold) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = txt; p.level = lvl
        p.font.size = Pt(size - 2 * lvl); p.font.bold = bold
        p.font.color.rgb = DARK
        p.space_after = Pt(8)


def img(s, path, left, top, width):
    s.shapes.add_picture(path, Inches(left), Inches(top), width=Inches(width))


# 1 Title
s = slide("Churn Analysis — UK Full-Fibre Broadband", "Case Study Data 1 · 10,000 customers · prepared with data through Sep 2025")
tb = s.shapes.add_textbox(Inches(0.6), Inches(3.2), Inches(12), Inches(2))
p = tb.text_frame.paragraphs[0]
p.text = "Understanding who leaves, why they leave, and what we can do about it."
p.font.size = Pt(20); p.font.color.rgb = DARK

# 2 Data & approach
s = slide("Data & Approach")
bullets(s, [
    (0, "Dataset: 10,000 customers across London, Manchester, Leeds and Nottingham", True),
    (1, "Fields: city, postcode, bundle speed, contract duration, competitor presence, activation/termination dates and reason", False),
    (0, "Cleaning performed", True),
    (1, "Excel serial dates converted; termination date '-' / blank treated as still active", False),
    (1, "Churn flag: has a termination date and a real termination reason → 6,947 churned, 3,053 active", False),
    (1, "Tenure measured to termination (churned) or to snapshot date Sep-2025 (active)", False),
    (0, "Overall churn rate in the base: 69.5% — unusually high, consistent with a churn-weighted sample", True),
    (1, "All findings below compare churn rates between segments, not absolute volumes", False),
])

# 3 Headline findings
s = slide("Headline Findings")
bullets(s, [
    (0, "Moving home dominates: 82% of all terminations are 'Moving Home / Going Away' — largely uncontrollable churn", True),
    (0, "Contract length is the strongest retention lever: 24-month contracts churn at 42.5% vs ~75% for monthly/12-month", False),
    (0, "Geography matters: Leeds (82%) and Manchester (77%) churn far above London (63%) and Nottingham (41%)", False),
    (0, "Entry-level 50Mb bundles churn most (82%); churn declines as speed rises — 1Gb at 66%", False),
    (0, "Controllable churn is small: price/deal (1.3%), complaints (0.5%), bad debt (5.5%)", False),
    (0, "Churned customers leave after a median of ~12 months — the contract-end cliff", False),
])

# 4 Reasons chart
s = slide("Why Customers Leave", "Termination reason distribution (6,947 churned customers)")
img(s, "charts/termination_reasons.png", 0.6, 1.5, 7.2)
bullets(s, [
    (0, "'Moving Home/Going Away' = 82% of churn", True),
    (1, "Fibre is address-bound: movers churn when the new home isn't served (no offnet product)", False),
    (0, "'Customer not leaving' (521) likely admin/revoked terminations — data-quality fix", False),
    (0, "True controllable churn (price, complaints) is only ~2%", False),
], left=8.1, top=1.7, width=4.7, size=15)

# 5 Contract + competitors
s = slide("Contract Length & Competition", "Longer contracts retain; competitor presence shows a mild effect")
img(s, "charts/churn_by_contract.png", 0.4, 1.6, 5.9)
img(s, "charts/churn_by_competitors.png", 6.9, 1.6, 5.9)
bullets(s, [
    (0, "24-month contracts cut churn nearly in half vs monthly rolling", True),
    (0, "Areas with 1+ competitors churn ~4pts more than uncontested areas; 2-competitor sample is tiny (n=40)", False),
], top=6.1, height=1.2, size=14)

# 6 Geography + bundle
s = slide("Where and What: Geography & Bundle")
img(s, "charts/churn_by_city.png", 0.4, 1.6, 5.9)
img(s, "charts/churn_by_bundle.png", 6.9, 1.6, 6.0)
bullets(s, [
    (0, "Leeds & Manchester churn ~15-20pts above London — likely higher overbuild/competition and housing churn", False),
    (0, "50Mb entry tier churns most — entry-tier customers are the most price-sensitive and mobile", False),
], top=6.1, height=1.2, size=14)

# 7 Tenure & timing
s = slide("When Customers Leave", "Median churned tenure ~12 months — churn concentrates at contract end")
img(s, "charts/tenure_hist.png", 0.4, 1.6, 6.0)
img(s, "charts/churn_time.png", 6.8, 1.6, 6.2)
bullets(s, [
    (0, "Churn spikes around the 12-month mark — contract expiry and intro-price rollover are the trigger", False),
    (0, "7.4% of churn happens within 3 months — early-life onboarding/installation issues", False),
], top=6.1, height=1.2, size=14)

# 8 Market context
s = slide("UK Fibre Market Context", "External factors that amplify the findings")
bullets(s, [
    (0, "Altnet footprint nearly doubled: ~16m premises passed by late 2025 (~57% of UK FTTP) — overbuild keeps rising", False),
    (0, "FTTP prices fell ~41% in real terms over 3 years — switching is cheap and heavily promoted", False),
    (0, "House moves are the industry's largest 'uncontrollable' churn driver, worsened by Stamp-Duty-driven moves; most altnets don't sell offnet, so movers are lost at the address boundary", False),
    (0, "Consolidation is coming (CityFibre capital raise, Netomnia/nexfibre deal) — scale players will gain wholesale reach into the mover market", False),
    (0, "Altnets hold ~11% retail share; Hyperoptic ~1.7% — retention economics matter more than share grabs", False),
    (1, "Sources: Intelligens Consulting (Dec 2025), 8Advisory FTTH take-up & churn (Jul 2025), Opensignal (Q2 2026), Enders Analysis Q2 2025", False),
])

# 9 Recommendations
s = slide("Recommendations")
bullets(s, [
    (0, "Attack the mover market (82% of churn)", True),
    (1, "Launch a mover's program: proactive 'we're at your new address' outreach, address-portability check, partnered install at move-in", False),
    (1, "Pursue wholesale/offnet partnerships (e.g. CityFibre, Openreach FTTP) so movers can stay customers at non-served addresses", False),
    (0, "Shift the base to longer contracts", True),
    (1, "Incentivise 24-month terms (price locks, free speed upgrades) — they halve churn", False),
    (0, "Pre-empt the 12-month cliff", True),
    (1, "Retention offers 60-90 days before contract end; re-contract before intro pricing rolls off", False),
    (0, "Fix early-life churn: onboarding quality checks and 90-day save-desk for new installs", False),
    (0, "Regional playbook for Leeds/Manchester: competitive win-back offers and service-quality audits where overbuild is densest", False),
    (0, "Data hygiene: reconcile 'Customer not leaving' records and add mover destination capture to measure recoverable churn", False),
])

# 10 Caveats
s = slide("Caveats & Next Steps")
bullets(s, [
    (0, "The base is churn-weighted (69.5%) — segment rates are relative, not absolute business churn", False),
    (0, "No pricing, usage or satisfaction fields — recommended next data pull: ARPU, monthly spend, fault tickets, NPS", False),
    (0, "Suggested next analyses: survival/hazard modelling by cohort, mover-destination capture rate, competitor-density heatmap by postcode district", False),
])

prs.save("Churn_Analysis.pptx")
print("saved Churn_Analysis.pptx")
