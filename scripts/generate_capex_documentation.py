"""Generate the economic/methodology and technical CapEx story guides as DOCX."""

from __future__ import annotations

import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import docx_ooxml as ooxml
from config import PROCESSED_DATA_DIR, PROJECT_ROOT
from config.capex_analysis import OUTPUTS


OUTPUT_DIR = PROJECT_ROOT / "docs"
ECONOMIC_GUIDE = OUTPUT_DIR / "CAPEX_STORY_ECONOMIC_AND_METHODOLOGY_GUIDE.docx"
TECHNICAL_GUIDE = OUTPUT_DIR / "CAPEX_STORY_TECHNICAL_GUIDE.docx"
GENERATED_AT = datetime.now(timezone.utc)


def load_artifact(key: str) -> dict:
    return json.loads((PROCESSED_DATA_DIR / OUTPUTS[key]).read_text(encoding="utf-8"))


def git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def configure_package(title: str, short_title: str) -> None:
    stamp = GENERATED_AT.isoformat()
    ooxml.CORE_PROPERTIES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>{escape(title)}</dc:title>
<dc:subject>India public capital-expenditure transmission research</dc:subject>
<dc:creator>2026DB project</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">{stamp}</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">{stamp}</dcterms:modified>
<cp:keywords>India; public capital expenditure; fiscal policy; investment; Nifty; debt sustainability; methodology</cp:keywords>
</cp:coreProperties>"""
    ooxml.HEADER = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="right"/><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="5" w:color="CBD5E1"/></w:pBdr></w:pPr><w:r><w:rPr><w:color w:val="64748B"/><w:sz w:val="17"/></w:rPr><w:t>{escape(short_title)}</w:t></w:r></w:p></w:hdr>"""
    ooxml.FOOTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:color w:val="64748B"/><w:sz w:val="17"/></w:rPr><w:t>India public CapEx transmission  •  </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:color w:val="64748B"/><w:sz w:val="17"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>"""


def title_page(doc: ooxml.DocxBuilder, title: str, subtitle: str, audience: str) -> None:
    doc.add_paragraph("2026DB RESEARCH PROGRAMME", runs=[doc.run("2026DB RESEARCH PROGRAMME", bold=True, color="D97706", size=18)], space_after=240)
    doc.add_paragraph(title, style="Title", keep_next=True)
    doc.add_paragraph(subtitle, style="Subtitle")
    doc.add_paragraph("", space_after=320)
    doc.add_callout(
        "Purpose",
        audience,
        color="1F4E78",
        shade="EAF2F8",
    )
    doc.table(
        ["Document control", "Value"],
        [
            ["Generated", GENERATED_AT.strftime("%d %B %Y, %H:%M UTC")],
            ["Repository revision", git_revision()],
            ["Research lens", "India’s public CapEx transmission"],
            ["Status", "Methodology and implementation documentation"],
            ["Primary question", "Did India’s public CapEx push transmit into sectoral and real economic growth strongly enough to justify its fiscal cost?"],
        ],
        widths=[2600, 6400],
    )
    doc.add_page_break()


def add_toc(doc: ooxml.DocxBuilder) -> None:
    doc.add_heading("Contents", 1)
    doc.add_paragraph("This field updates automatically when the document is opened in Microsoft Word. If it does not, select the field and choose Update Field.")
    doc.body.append(
        '<w:p><w:fldSimple w:instr="TOC \\o &quot;1-3&quot; \\h \\z \\u">'
        '<w:r><w:rPr><w:color w:val="64748B"/></w:rPr><w:t>Update this field to generate the table of contents.</w:t></w:r>'
        '</w:fldSimple></w:p>'
    )
    doc.add_page_break()


def add_stage_header(doc: ooxml.DocxBuilder, title: str, question: str, role: str) -> None:
    doc.add_heading(title, 1)
    doc.add_callout("Question answered", question, color="2E7D6B", shade="ECFDF5")
    doc.add_paragraph(role)


def add_metric_table(doc: ooxml.DocxBuilder, rows: list[list[str]]) -> None:
    doc.table(
        ["Metric", "Economic justification", "Production and formula", "Interpretation and limitations"],
        rows,
        widths=[1500, 2300, 2700, 2500],
        font_size=15,
    )


def central_scenario(starting_debt: float) -> dict[str, float]:
    capex = 0.5
    execution = 0.90
    multiplier = 1.0
    lag = 1
    crowd_in = 0.15
    overrun = 0.10
    borrowing_share = 0.75
    interest = 0.07
    growth = 0.10
    revenue_share = 0.15
    primary_balance = -2.0
    delivered = capex * execution
    productive = delivered / (1 + overrun)
    annual_impact = productive * (multiplier + crowd_in)
    incremental_debt = 0.0
    cumulative_gdp = 0.0
    debt_change = 0.0
    baseline_debt = starting_debt
    for year in range(1, 6):
        baseline_debt = baseline_debt * (1 + interest) / (1 + growth) - primary_balance
        benefit = annual_impact if year > lag else 0.0
        cumulative_gdp += benefit
        revenue = benefit * revenue_share
        borrowing = delivered * borrowing_share
        incremental_debt = incremental_debt * (1 + interest) / (1 + growth) + borrowing - revenue
        scenario_debt = (baseline_debt + incremental_debt) / (1 + cumulative_gdp / 100)
        debt_change = scenario_debt - baseline_debt
    return {
        "delivered": delivered,
        "productive": productive,
        "annual_impact": annual_impact,
        "cumulative_gdp": cumulative_gdp,
        "debt_change": debt_change,
        "gdp_per_rupee": cumulative_gdp / (capex * 5),
    }


def build_economic_guide() -> None:
    execution = load_artifact("execution")
    allocation = load_artifact("allocation")
    delivery = load_artifact("delivery")
    production = load_artifact("production")
    sectors = load_artifact("sectors")
    correlations = load_artifact("correlations")
    private = load_artifact("private")
    fiscal = load_artifact("fiscal")
    summary = load_artifact("summary")
    corporate = load_artifact("corporate")
    quality = load_artifact("quality")
    states = load_artifact("states")
    crowding_in = load_artifact("crowding_in")

    doc = ooxml.DocxBuilder()
    configure_package(
        "India’s Public CapEx Transmission: Economic and Methodology Guide",
        "CapEx transmission  |  Economic and methodology guide",
    )
    title_page(
        doc,
        "India’s Public CapEx Transmission",
        "Economic rationale, measurement methodology, interpretation and scenario-model guide",
        "This document is for economists, research analysts and reviewers. It explains why each stage exists, how every metric is constructed, what a movement means, what it does not mean, and how the final five-year scenario model converts assumptions into conditional GDP and debt paths.",
    )
    add_toc(doc)

    doc.add_heading("1. Executive summary", 1)
    doc.add_paragraph(
        "The research story asks whether a sustained increase in central-government capital expenditure "
        "has travelled through a plausible transmission chain: first into executed public spending, then into "
        "sector allocations and physical delivery, market expectations, corporate fundamentals, private "
        "investment and productive output, and finally into a fiscal position capable of sustaining the policy. "
        "The design deliberately separates these links because a larger budget is not the same thing as a "
        "completed asset, a higher equity index is not the same thing as real investment, and a growth effect "
        "is not automatically large enough to offset debt-service costs."
    )
    doc.table(
        ["Stage", "Economic question", "Principal evidence", "Current inference"],
        [
            ["1. Policy input", "Did the Centre materially increase CapEx and execute the plan?", "CapEx/GDP, expenditure share, BE–RE–actual, execution ratio", "The intensity hypothesis is classified as supported."],
            ["1B. Allocation and delivery", "Where was funding directed, and did physical outputs follow?", "Roads/Railways capital BE; highway construction; railway electrification", "Budget scale and selected outputs are visible, but they are not a benefit-cost evaluation."],
            ["1C. Investment quality", "Were monitored projects delivered on time and near original cost?", "Project status, delay shares and anticipated-versus-original cost", "Delivery quality is now observable by sector, subject to the 2011 coverage break."],
            ["2A. Market response", "Did CapEx-sensitive sectors re-rate relative to broad and defensive markets?", "Official Nifty total-return indices", "Useful expectation evidence, not real-economy proof."],
            ["2B. Timing", "Did recorded CapEx precede returns, or did markets move first?", "Lead/lag Pearson and Spearman correlations; scatter plots", "Associational and sample-limited; the forward sector hypothesis remains supported under the deterministic rule."],
            ["2C. Firms", "Did the re-rating coincide with stronger business fundamentals?", "Frozen ten-company medians", "A case study that reduces size domination but does not represent the full index."],
            ["2D. Conversion", "Did productive capacity and private fixed investment respond?", "Private corporate GFCF, OBICUS utilisation, capital-goods IIP", "Current aligned evidence remains inconclusive."],
            ["2E. Crowding-in ladder", "Which private and production outcomes follow CapEx, and at what lag?", "Registered 0–3 year correlations with an eight-observation gate", "National private-investment samples remain insufficient; coefficients are descriptive."],
            ["2F. State evaluation", "Do within-state capital-outlay changes precede real growth?", "29-state, 12-year two-way fixed-effects panel", "Eligible associational estimate; explicitly not a causal multiplier."],
            ["3. Fiscal cost", "Can the strategy coexist with debt-service pressure?", "Debt/GDP, interest burden, primary balance, CapEx/interest allocation", "Current evidence is classified as partially supportive."],
            ["4. Scenario lab", "Under what assumptions could more CapEx improve output without worsening debt/GDP?", "Dynamic debt baseline, uncertainty bands, sensitivity, frontier and backtest", "A reproducible conditional risk model, not an econometric forecast."],
        ],
        widths=[1500, 2600, 2900, 2000],
        font_size=15,
    )
    doc.add_callout(
        "Central conclusion",
        "The evidence is strongest for the policy input and market-response links, weaker for private-investment conversion, and conditional for fiscal sustainability. This asymmetry is the substantive finding: the project does not treat a larger budget or higher sector index as proof that the entire transmission chain worked.",
        color="A33D4A",
        shade="FFF1F2",
    )

    doc.add_heading("2. Economic framework and identification boundary", 1)
    doc.add_heading("The transmission chain", 2)
    doc.add_code(
        "Budgeted public CapEx → execution → sector allocation → completed infrastructure → lower costs / higher capacity → market expectations → corporate revenue and investment → private GFCF and capital-goods output → growth and revenue feedback → debt and interest burden"
    )
    doc.add_paragraph(
        "Public investment can raise demand during construction and expand supply after an asset enters service. "
        "The short-run channel operates through procurement, wages and intermediate inputs. The medium-run channel "
        "can operate through lower logistics costs, improved reliability, network effects, higher expected demand "
        "and complementary private investment. Against these benefits sit implementation lags, leakage, cost "
        "overruns, low utilisation, crowding out, higher borrowing and interest costs. Each stage therefore tests "
        "a distinct necessary or supporting condition rather than assuming one aggregate multiplier."
    )
    doc.add_heading("What this design can and cannot identify", 2)
    for item in [
        "Time ordering is informative but not causal identification. Markets can anticipate budgets; governments can raise CapEx in response to weakness; both can respond to a third factor.",
        "Correlations describe co-movement. They do not isolate CapEx from monetary policy, commodity cycles, global risk appetite, elections, reforms, corporate leverage or base effects.",
        "The physical measures confirm selected outputs, not quality-adjusted capital services. A kilometre of road or electrified route is not homogeneous across terrain, lane width, congestion relief or economic value.",
        "Private corporate GFCF is not the entire private sector. Household and unincorporated investment are outside that institutional numerator.",
        "The scenario lab is a transparent conditional projection. It is not trained on the small correlation sample and does not claim a statistically estimated multiplier.",
    ]:
        doc.add_bullet(item)

    doc.add_heading("3. Measurement conventions", 1)
    doc.table(
        ["Convention", "Meaning in this project", "Common misreading prevented"],
        [
            ["Fiscal-year date", "FY2024–25 is plotted at 31 March 2025 and retains the FY label.", "Mistaking a fiscal period for calendar-year activity."],
            ["Status", "Actual, revised, provisional, estimate and budget are retained.", "Treating a plan or early estimate as an out-turn."],
            ["Nominal", "CapEx growth uses current-price rupees.", "Reading nominal growth as a change in real project volume."],
            ["Ratio", "Numerator and denominator coverage are stated explicitly.", "Comparing central flows with general-government stocks as if institutional coverage were identical."],
            ["Index", "A rebased series communicates proportional movement, not rupee value.", "Treating an index level of 150 as a 150% return."],
            ["Relative wealth", "Sector TRI wealth divided by Nifty 50 TRI wealth, rebased to 100.", "Confusing absolute gains with outperformance."],
            ["Lead/lag", "Identifies observation order and window separation.", "Interpreting ‘leads’ as causation."],
            ["Null", "Unavailable or undefined; never converted to zero.", "Creating false observations or joining across gaps."],
        ],
        widths=[1700, 4300, 3000],
    )

    add_stage_header(
        doc,
        "4. Stage 1 — Public CapEx intensity and execution",
        "Did central-government capital expenditure become a larger policy input, and was the original plan delivered?",
        "This stage establishes the treatment-like policy impulse. Without a material and executed increase in CapEx, downstream market or investment movements cannot plausibly be described as transmission from a CapEx push.",
    )
    add_metric_table(doc, [
        ["Actual CapEx", "The realised fiscal resource committed to asset creation is the core policy input.", "Union Budget actual central capital expenditure, ₹ crore. Multiple budget vintages preserve the final out-turn rather than silently substituting later plans.", "A higher level may reflect scale, inflation or reclassification. It says nothing by itself about GDP intensity, asset quality or completion."],
        ["Budget Estimate (BE)", "Captures the government’s original policy intention before in-year information and supplementary decisions.", "The original BE is retained from the edition in which that fiscal year was the current budget year.", "Useful for testing execution. It is a plan, not realised demand or completed infrastructure."],
        ["Revised Estimate (RE)", "Shows the in-year reassessment after early execution information.", "The RE is taken from the following budget vintage for the same fiscal year.", "BE-to-RE changes can reflect implementation, reprioritisation or macro shocks; they are not a clean efficiency measure."],
        ["CapEx execution ratio", "Separates headline ambition from delivery against the initial allocation.", "100 × Actual CapEx / original BE.", "100% means actual matched BE. Above 100% can follow supplementary appropriations; below 100% can indicate under-execution or changed plans."],
        ["Actual CapEx / GDP", "Measures macroeconomic effort relative to the size of the economy.", "100 × actual central CapEx / nominal GDP from a compatible fiscal year.", "A rising ratio is stronger evidence of intensification than a rising rupee level, but remains nominal and central-government only."],
        ["Actual CapEx / total expenditure", "Measures budget composition and the opportunity cost relative to other spending.", "100 × actual central CapEx / actual central total expenditure.", "A higher share indicates greater capital orientation, not necessarily better welfare outcomes."],
        ["Nominal CapEx growth", "Supplies the annual change used in timing tests.", "100 × (CapExₜ / CapExₜ₋₁ − 1).", "Contains inflation and base effects. The project never labels it real CapEx growth."],
    ])
    doc.add_paragraph(
        f"The current execution artifact contains {len(execution['series'])} series from "
        f"{execution['metadata']['start_date']} to {execution['metadata']['end_date']}. Its hypothesis rule asks "
        "whether both CapEx/GDP and the CapEx expenditure share are higher at the end of the observed comparison "
        "than at the beginning. This is a directional classification, not a significance test."
    )

    add_stage_header(
        doc,
        "5. Stage 1B — Sector allocation and physical delivery",
        "How much central-budget capital support went to Roads and Railways, and did selected physical outputs materialise?",
        "This bridge was added to prevent a leap from aggregate public spending directly to equity-market performance. It distinguishes financial input from observable infrastructure delivery.",
    )
    add_metric_table(doc, [
        ["Railways central-budget CapEx", "Railways are a major network-infrastructure channel through which public capital can affect freight capacity, travel time, energy use and regional connectivity.", "Budget Estimate from the capital column of Union Budget Expenditure Profile Statement 3. Internal resources and extra-budgetary resources are excluded for comparability with Roads.", "Shows central-budget support, not total railway capital outlay and not actual execution."],
        ["Roads central-budget CapEx", "Road investment can lower travel time and logistics costs, expand market access and complement industrial investment.", "Budget Estimate from the capital—not total—column for the Ministry of Road Transport and Highways.", "The historical series was reconciled across four budget vintages. Revenue expenditure is excluded."],
        ["National highways constructed", "A physical output tests whether funding coincided with completed road length.", "Fiscal-year kilometres reported by MoRTH.", "Does not adjust for lane width, strengthening versus greenfield construction, terrain, quality, maintenance or economic usage."],
        ["Railway route kilometres electrified", "Electrification is a measurable railway-modernisation output with potential operating-cost and energy implications.", "Broad-gauge route kilometres electrified during the fiscal year, reported by Indian Railways.", "It is not new track, freight capacity, punctuality or total railway output. Completion naturally slows as the network approaches saturation."],
    ])
    doc.add_callout(
        "Unit separation",
        "Financial allocations and physical kilometres are separate artifacts and separate views. They cannot be activated on one chart. This is both a visual-design decision and a methodological safeguard against implying a cardinal relationship between incomparable units.",
        color="2E7D6B",
        shade="ECFDF5",
    )
    doc.add_paragraph(
        f"The allocation asset has {sum(len(x['values']) for x in allocation['series'].values())} observations; "
        f"the delivery asset has {sum(len(x['values']) for x in delivery['series'].values())}. "
        "Neither series estimates rupees per kilometre because the spending categories and delivered outputs do "
        "not map one-to-one by project, vintage or completion year."
    )
    rail_alloc = {
        row["period_label"]: row["value"]
        for row in allocation["series"]["railways_budget_capex"]["values"]
    }
    road_alloc = {
        row["period_label"]: row["value"]
        for row in allocation["series"]["roads_budget_capex"]["values"]
    }
    doc.add_heading("Published allocation observations", 2)
    doc.table(
        ["Fiscal year", "Railways capital BE (₹ crore)", "Roads capital BE (₹ crore)", "Status"],
        [
            [
                period,
                f"{rail_alloc[period]:,.2f}",
                f"{road_alloc[period]:,.2f}",
                "Budget Estimate",
            ]
            for period in rail_alloc
        ],
        widths=[1800, 2800, 2800, 1600],
    )
    highway = {
        row["period_label"]: row["value"]
        for row in delivery["series"]["national_highways_constructed_km"]["values"]
    }
    electrified = {
        row["period_label"]: row["value"]
        for row in delivery["series"]["railway_route_km_electrified"]["values"]
    }
    doc.add_heading("Published physical-delivery observations", 2)
    doc.table(
        ["Fiscal year", "National highways constructed (km)", "Railway route electrified (Rkm)"],
        [[period, f"{highway[period]:,.0f}", f"{electrified[period]:,.0f}"] for period in highway],
        widths=[2000, 3700, 3300],
    )

    add_stage_header(
        doc,
        "6. Stage 2A — CapEx-sensitive market response",
        "Did sectors expected to benefit from the CapEx cycle outperform the broad market, and did they differ from a defensive control?",
        "Markets aggregate expectations about future cash flows, discount rates and risk. They can react before expenditure appears in annual accounts, which makes them informative about expectations but unsuitable as proof of realised productive investment.",
    )
    add_metric_table(doc, [
        ["Nifty Capital Goods TRI", "Direct exposure to machinery, electrical equipment, engineering and investment-cycle demand.", "Official total-return index including reinvested distributions; sampled at the last available observation of each month.", "Strong performance may reflect domestic investment expectations, order cycles or valuation changes; attribution to government CapEx is not automatic."],
        ["Nifty Infrastructure TRI", "Broader exposure to infrastructure operators, builders and related sectors.", "Official TRI, aligned to the common monthly sample.", "Composition is heterogeneous and can respond to regulation, commodity prices and financing conditions."],
        ["Nifty India Manufacturing TRI", "Tests whether the investment narrative extends beyond a narrow capital-goods basket.", "Official TRI on the same common dates.", "Captures wider manufacturing expectations and may dilute direct CapEx sensitivity."],
        ["Nifty 50 TRI", "Provides the broad-market opportunity-cost benchmark.", "Official TRI. Standalone series are independently rebased to 100; relative wealth divides sector wealth by Nifty 50 wealth.", "A sector can rise in rupees yet underperform the broad market."],
        ["Nifty FMCG TRI", "Provides a defensive, consumption-oriented comparison less directly linked to infrastructure investment.", "Official TRI displayed as a standalone rebased line; target-minus-FMCG returns are computed only inside the timing analysis.", "FMCG is a control comparison, not a formal untreated counterfactual."],
        ["Relative wealth index", "Measures compounded outperformance rather than a single-period return gap.", "100 × cumulative product[(1+r_sector)/(1+r_Nifty50)].", "Above 100 means cumulative outperformance since the common start; it does not imply causal gains from CapEx."],
    ])
    doc.add_paragraph(
        f"The common market sample runs from {sectors['metadata']['start_date']} to "
        f"{sectors['metadata']['end_date']} across {len(sectors['markets'])} official TRI histories. "
        "Using one common date matrix prevents an index with shorter coverage from being compared over a more "
        "favourable interval."
    )

    add_stage_header(
        doc,
        "7. Stage 2B — Timing and correlation explorer",
        "Does CapEx growth occur before sector returns, or do market returns occur before the recorded fiscal observation?",
        "This stage replaces a visually persuasive dual-axis line chart with explicit paired fiscal-year observations, correlation coefficients, sample counts, sensitivity checks and scatter plots.",
    )
    doc.add_heading("Window construction", 2)
    doc.table(
        ["Direction", "Registered windows", "Outcome construction", "Economic interpretation"],
        [
            ["CapEx leads", "0, 6 and 12 months", "Compound monthly return over the subsequent 12 months after the selected delay.", "Tests whether stronger recorded CapEx growth is followed by stronger market performance."],
            ["Market leads", "3, 6 and 12 months", "Compound monthly return over the 12-month window ending before the fiscal-year CapEx observation.", "Tests anticipation, prior budget information or reverse timing."],
            ["Private GFCF", "0, 1 and 2 fiscal years", "Private corporate GFCF/GDP aligned to the CapEx year at the fixed annual lag.", "A real-economy lag test, currently too short for a reliable inference."],
        ],
        widths=[1700, 1800, 3100, 2400],
    )
    add_metric_table(doc, [
        ["Pearson correlation", "Measures linear co-movement and is directly related to the slope of a standardised linear fit.", "Cov(X,Y)/(σXσY) on complete fiscal-year pairs.", "+1 is perfect positive linear association, −1 perfect negative, 0 no linear association. Highly sensitive to outliers in small samples."],
        ["Spearman correlation", "Checks whether the relationship is broadly monotonic without requiring linear spacing.", "Pearson correlation of the ranked observations.", "More resistant to extreme magnitudes, but still unstable with few years and does not establish causality."],
        ["Pandemic exclusion", "Tests whether exceptional FY2020–21 and FY2021–22 observations dominate the coefficient.", "Recompute Pearson after removing fiscal ends 2021 and 2022.", "A sensitivity check, not permission to discard inconvenient observations. Spearman uses the full sample in the interface."],
        ["OLS line of best fit", "Provides a visual summary of direction and influential points.", "ŷ = α + βx fitted to the currently displayed scatter sample.", "The line is descriptive; no confidence interval or causal interpretation is attached."],
        ["Sample size n", "Makes the evidence constraint visible.", "Count of complete aligned pairs after the selected window and exclusions.", "Cells with n < 4 are labelled insufficient. Even n ≥ 4 remains exploratory."],
    ])
    doc.add_paragraph(
        f"The artifact contains {len(correlations['metadata']['correlation_estimates'])} registered estimates: "
        "forward market windows, reverse market windows and private-GFCF windows. The summary verdict uses only "
        "forward, sector-level market relationships with at least four pairs. Reverse leads and Nifty 50 are "
        "excluded from the forward-transmission classification."
    )
    doc.add_callout(
        "Why both directions are retained",
        "If the market-leads coefficient is stronger than the CapEx-leads coefficient, the evidence may be more consistent with anticipation than with a return generated after expenditure. Keeping both directions therefore weakens overclaiming; it does not duplicate the same question.",
        color="A33D4A",
        shade="FFF1F2",
    )

    add_stage_header(
        doc,
        "8. Stage 2C — Corporate fundamentals case study",
        "Did sector optimism coincide with stronger revenue, earnings, company investment and productive assets?",
        "Market prices can rise without a corresponding improvement in operating performance. The corporate layer checks a frozen group of firms without pretending to reconstruct the full indices.",
    )
    add_metric_table(doc, [
        ["Revenue growth", "Tests whether demand and project activity reached company sales.", "Company-level year-on-year total-revenue growth; unweighted median by group and reporting year.", "Can be nominal, acquisition-driven or affected by reporting dates. Median growth is not aggregate sector revenue."],
        ["EBITDA growth", "Adds an operating-earnings check to revenue growth.", "Company-level EBITDA or documented fallback operating measure, then group median.", "Accounting definitions and exceptional items vary across providers and companies."],
        ["Company CapEx growth", "Tests whether exposed firms themselves increased investment.", "Absolute cash-flow capital expenditure; within-company growth before aggregation.", "Cash-flow classification may vary and growth can be extreme from a small base."],
        ["Net PPE growth", "Measures growth in the productive-asset stock after depreciation and disposals.", "Year-on-year net property, plant and equipment growth; group median.", "Net PPE can fall despite gross investment when depreciation or disposals are high."],
        ["Debt growth", "Shows whether expansion was accompanied by greater leverage.", "Year-on-year total-debt growth; group median.", "Debt can finance working capital, acquisitions or refinancing rather than productive CapEx."],
        ["ROCE proxy", "Introduces an efficiency measure rather than focusing only on scale.", "100 × EBIT / (total assets − current liabilities).", "A provider-based proxy, not the company’s own reported ROCE; denominator definitions differ."],
    ])
    doc.add_paragraph(
        f"The frozen basket contains {len(corporate['metadata']['company_coverage'])} companies: five capital-goods "
        "and five infrastructure cases. Growth is calculated inside each company before taking the median, "
        "which avoids allowing the largest company to determine the group rate. It does not solve survivorship, "
        "selection or accounting-comparability concerns."
    )

    add_stage_header(
        doc,
        "9. Stage 2D — Private investment and productive conversion",
        "Did public investment coincide with higher private fixed investment, tighter capacity and capital-goods output?",
        "This is the most demanding transmission stage. It asks whether market expectations and public infrastructure were converted into realised private investment and production.",
    )
    add_metric_table(doc, [
        ["Private corporate GFCF / GDP", "Measures private corporate fixed-capital formation relative to economic scale.", "100 × (private non-financial corporation GFCF + private financial corporation GFCF) / nominal GDP, within one MoSPI base-year vintage.", "Excludes households and unincorporated enterprises. A lower ratio can coexist with rising nominal investment if GDP grows faster."],
        ["Private corporate share of total GFCF", "Shows the institutional composition of economy-wide fixed investment.", "100 × private corporate GFCF / total GFCF.", "Not a public-versus-private binary because household and other institutional sectors remain in total GFCF."],
        ["Manufacturing capacity utilisation", "High utilisation can create an incentive to add capacity and helps distinguish idle assets from binding demand.", "RBI OBICUS unadjusted quarterly aggregate for responding manufacturers.", "A changing voluntary sample and seasonality limit comparability. High utilisation is not itself new investment."],
        ["Public CapEx lagged one year", "Provides a transparent visual timing comparator for possible crowding-in.", "Actual public CapEx/GDP shifted forward one fiscal year.", "The shift is a hypothesis display, not an estimated distributed lag."],
        ["Capital-goods IIP", "Measures real productive output in machinery and equipment categories used for further investment.", "NSO use-based capital-goods IIP, fiscal-year average, base 2011–12=100.", "Volatile, currently ending FY2022–23, and not a direct measure of orders, ownership or profitability."],
    ])
    doc.add_paragraph(
        f"The private-response artifact contains {sum(len(x['values']) for x in private['series'].values())} "
        f"observations and the capital-goods IIP artifact contains {sum(len(x['values']) for x in production['series'].values())}. "
        "The short consistent private-corporate GFCF history is the principal reason the current real-economy "
        "classification is inconclusive."
    )
    doc.add_heading("Published capital-goods IIP observations", 2)
    doc.table(
        ["Fiscal year", "Capital-goods IIP (2011–12=100)", "Status"],
        [
            [row["period_label"], f"{row['value']:.1f}", row.get("status", "actual")]
            for row in production["series"]["capital_goods_iip"]["values"]
        ],
        widths=[2500, 4000, 2500],
    )

    add_stage_header(
        doc,
        "10. Stage 1C — Investment quality and project delivery",
        "Did a larger public-investment envelope produce timely, cost-controlled assets?",
        "This stage closes the gap between financial execution and asset quality by using MoSPI-monitored central-sector project status and cost histories published by RBI.",
    )
    add_metric_table(doc, [
        ["Projects monitored", "Defines the implementation universe behind the quality ratios.", "Sum of ahead, on-schedule, delayed and without-commissioning-date projects by sector and end-March year.", "The threshold changes from ₹100 crore to ₹150 crore in 2011, so levels are not a seamless project-population series."],
        ["Ahead/on-schedule share", "Measures whether monitored assets remain on their registered delivery path.", "100 × (ahead + on schedule) / monitored projects.", "A project can be on schedule yet low quality or low value; schedule revisions can affect classification."],
        ["Delayed share", "Captures implementation friction that can defer network and supply benefits.", "100 × delayed / monitored projects.", "From 2011 delay is measured against the original schedule; the break is shown in the chart."],
        ["Cost-overrun percentage", "Tests how much productive asset is obtained for the original fiscal commitment.", "100 × (anticipated cost − original cost) / original cost for delayed projects.", "Inflation, scope changes and improved specifications can raise anticipated cost; the measure is a warning signal, not a welfare loss estimate."],
    ])
    latest_quality = quality["series"]["delayed_share"]["values"][-1]
    doc.add_paragraph(
        f"At end-March {latest_quality['date'][:4]}, delayed projects represented {latest_quality['value']:.1f}% "
        "of the monitored all-sector universe. The interactive sector map pairs delay and cost-overrun shares and sizes each point by monitored-project count."
    )

    add_stage_header(
        doc,
        "11. Stage 2E — Crowding-in distributed-lag evidence ladder",
        "Do private-investment, capacity and capital-goods outcomes follow central CapEx growth?",
        "Four outcomes are aligned at fixed zero- through three-year leads. A coefficient is withheld from inference until eight annual observations are available.",
    )
    doc.add_paragraph(
        f"The artifact registers {len(crowding_in['metadata']['lag_estimates'])} outcome-lag cells. "
        "Pearson measures linear association and Spearman measures rank association. The direct private-GFCF history has only three aligned observations per current lag, so even visually large coefficients remain labelled insufficient. Capital-goods production adds triangulation but is explicitly not relabelled as private investment."
    )
    doc.add_callout(
        "Inference discipline",
        "An eight-observation gate is still a minimal associational threshold, not a causal standard. Passing it would allow a coefficient to be discussed as an association; it would not identify an exogenous public-investment shock.",
        color="A33D4A", shade="FFF1F2",
    )

    add_stage_header(
        doc,
        "12. Stage 2F — State capital-outlay evaluation",
        "Do changes in a state’s capital-outlay intensity precede changes in its real growth?",
        "Actual capital outlay is scaled by current-price GSDP and paired with subsequent constant-price GSDP growth. State and fiscal-year fixed effects remove persistent state differences and common annual shocks.",
    )
    state_estimate = states["metadata"]["panel_estimate"]
    add_metric_table(doc, [
        ["State capital outlay/GSDP", "Makes fiscal effort comparable across differently sized states.", "100 × capital outlay in ₹ crore / current-price GSDP converted from ₹ lakh to ₹ crore.", "It measures outlay, not completed-project stock, maintenance, central projects located in the state or asset quality."],
        ["Next-year real GSDP growth", "Tests a transparent forward timing channel rather than same-year co-movement.", "100 × (constant-price GSDPₜ₊₁ / constant-price GSDPₜ − 1).", "Growth is affected by agriculture, services, disasters, transfers, policy and base effects."],
        ["Two-way fixed-effects coefficient", "Uses within-state variation while removing common year shocks.", "Both variables are demeaned by state and fiscal year; standard errors are clustered by state.", "Time-varying confounding, project selection and reverse causality remain, so the coefficient is associational."],
    ])
    interval = state_estimate["confidence_interval_95"]
    doc.add_paragraph(
        f"The eligible panel contains {state_estimate['n']} observations, {state_estimate['states']} states and "
        f"{state_estimate['years']} fiscal years. Its coefficient is {state_estimate['coefficient']:+.2f} percentage "
        f"points of next-year real growth per one percentage-point change in capital outlay/GSDP, with a state-clustered 95% interval of {interval[0]:.2f} to {interval[1]:.2f}. This is not a causal state multiplier."
    )

    add_stage_header(
        doc,
        "13. Stage 3 — Fiscal capacity and debt sustainability",
        "Did the CapEx strategy preserve enough fiscal capacity to remain credible and repeatable?",
        "A productive investment programme can still become unsustainable if borrowing costs, primary deficits or debt stocks dominate its growth and revenue benefits. The project therefore links transmission evidence back to fiscal constraints.",
    )
    add_metric_table(doc, [
        ["General-government debt / GDP", "Captures the combined stock burden of Centre and states relative to output.", "Published adjusted combined liabilities/GDP from RBI fiscal statistics.", "A stock ratio with broader institutional coverage than the central interest-flow metrics. No universal threshold is encoded."],
        ["Interest payments / revenue", "Measures how much central revenue is pre-committed to servicing debt.", "100 × interest-payments/GDP ÷ revenue-receipts/GDP; the shared GDP denominator cancels.", "A higher ratio implies less revenue flexibility, but says nothing about maturity or currency risk."],
        ["Interest payments / expenditure", "Places debt service against the full spending envelope.", "100 × interest-payments/GDP ÷ total-expenditure/GDP.", "Useful for allocation pressure; not a measure of the interest rate on debt."],
        ["Primary balance / GDP", "Separates current fiscal policy from interest inherited on the debt stock.", "Negative of RBI gross primary deficit/GDP, so deficits are shown below zero.", "A primary deficit is not automatically unsustainable when growth exceeds financing costs."],
        ["Actual CapEx share of expenditure", "Places productive allocation beside debt-service allocation on a comparable denominator.", "Actual central CapEx / actual central expenditure.", "Central coverage; should not be directly equated with general-government debt coverage."],
        ["CapEx-to-interest allocation ratio", "Summarises the relative budget shares devoted to capital formation and interest.", "(CapEx/expenditure) ÷ (interest/expenditure).", "₹ of CapEx share per ₹1 represented by interest share. Not a project return, fiscal multiplier or debt threshold."],
    ])
    doc.add_paragraph(
        "The fiscal quadrant uses sample medians only to organise observations into high/low CapEx and high/low "
        "interest regions. Dot colour represents debt/GDP. The medians are descriptive reference lines, not "
        "policy targets. Sustainability ultimately depends on the interest-growth differential, primary balance, "
        "maturity, inflation, contingent liabilities and the quality of the assets created."
    )

    doc.add_heading("14. Deterministic hypothesis summary", 1)
    rows = []
    for item in summary["hypotheses"]:
        rows.append([item["key"], item["hypothesis"], item["status"], item["interpretation"], item["caveat"]])
    doc.table(
        ["Hypothesis", "Claim", "Status", "Rule interpretation", "Boundary"],
        rows,
        widths=[1500, 2600, 1300, 2100, 1500],
        font_size=14,
    )
    doc.add_paragraph(
        "The summary is rule-generated so the displayed verdict does not depend on manually written prose after "
        "seeing the result. It remains deliberately conservative. ‘Supported’ means the registered indicators "
        "move in the hypothesised direction under the rule; it does not mean a causal effect has been estimated."
    )

    doc.add_heading("15. Stage 4 — Five-year CapEx scenario model", 1)
    doc.add_callout(
        "Correct label",
        "The interface is a conditional risk model. It is not an econometric forecast and does not estimate multiplier parameters from the historical correlations. Its P10/P50/P90 paths are simulated scenario percentiles from registered assumption ranges, not statistical confidence intervals.",
        color="A33D4A",
        shade="FFF1F2",
    )
    doc.add_heading("Purpose and baseline", 2)
    settled_debt = [
        row for row in fiscal["series"]["general_government_debt_pct_gdp"]["values"]
        if row.get("value") is not None and row.get("status") not in {"budget", "estimate"}
    ][-1]
    starting_debt = float(settled_debt["value"])
    doc.add_paragraph(
        f"The model begins from the latest non-budget general-government debt observation: "
        f"{starting_debt:.2f}% of GDP for {settled_debt.get('period_label')}. The baseline now evolves for five years "
        "under the exact debt equation using the selected interest rate, nominal growth and primary balance. The "
        "CapEx result is reported relative to that dynamic baseline rather than to an artificial flat debt ratio."
    )
    doc.add_heading("Inputs", 2)
    doc.table(
        ["Parameter", "Meaning", "Central preset", "Sensitivity role"],
        [
            ["Additional annual CapEx C", "Extra budgeted CapEx sustained in each of five years, % of GDP.", "0.5%", "Sets programme scale."],
            ["Execution e", "Share of the additional allocation actually spent.", "90%", "Affects delivery and borrowing."],
            ["Fiscal multiplier m", "Direct GDP effect per unit of productive investment.", "1.0×", "Principal transmission assumption."],
            ["Implementation lag L", "Whole years before each year’s GDP effect begins.", "1 year", "Delays growth and revenue feedback."],
            ["Private response q", "Private investment induced per unit of productive public investment.", "+0.15×", "Positive is crowding in; negative is crowding out."],
            ["Cost overrun o", "Extra cost that reduces productive output from executed spending.", "10%", "Separates spending from effective capital."],
            ["Borrowing share f", "Share of executed additional CapEx financed by incremental borrowing.", "75%", "Determines the direct debt addition."],
            ["Interest rate i", "Effective nominal financing rate on incremental debt.", "7%", "Rolls the debt stock forward."],
            ["Nominal growth g", "Baseline nominal GDP growth.", "10%", "Dilutes inherited incremental debt."],
            ["Primary balance pb", "Baseline revenue less non-interest expenditure; deficits are negative.", "−2% of GDP", "Moves the entire baseline debt path."],
            ["Revenue feedback τ", "Share of modelled additional GDP returned as government revenue.", "15%", "Offsets part of incremental borrowing."],
            ["Uncertainty scale u", "Scales registered ranges around ten economic assumptions.", "100%", "Controls scenario dispersion; zero collapses to the deterministic path."],
        ],
        widths=[1900, 3600, 1500, 2000],
        font_size=15,
    )
    doc.add_heading("Equations", 2)
    doc.add_code("Executed CapEx:                 E = C × e")
    doc.add_code("Productive investment:          P = E / (1 + o)")
    doc.add_code("Annual GDP effect after lag:    B = P × (m + q)")
    doc.add_code("Revenue feedback in year t:     Rₜ = τ × Bₜ")
    doc.add_code("Dynamic baseline debt:          dᵇₜ = dᵇₜ₋₁ × (1+i)/(1+g) − pb")
    doc.add_code("Incremental debt ratio:         Dₜ = Dₜ₋₁ × (1+i)/(1+g) + E×f − Rₜ")
    doc.add_code("Cumulative GDP effect:          Gₜ = Σ Bₛ through year t")
    doc.add_code("Scenario debt/GDP:              dₜ = (dᵇₜ + Dₜ) / (1 + Gₜ/100)")
    doc.add_code("Five-year GDP per ₹1 CapEx:     G₅ / (5C)")
    doc.add_paragraph(
        "All fiscal quantities are expressed as percentage points of GDP. Cost overruns reduce the productive "
        "capital obtained from executed spending. Borrowing is applied to executed—not merely announced—CapEx. "
        "The model then rolls incremental debt by the nominal interest-growth factor, subtracts revenue feedback "
        "and allows the cumulative GDP effect to expand the denominator."
    )
    doc.add_heading("Central-preset worked example", 2)
    central = central_scenario(starting_debt)
    doc.table(
        ["Output", "Central-preset result", "How to read it"],
        [
            ["Executed additional CapEx", f"{central['delivered']:.2f}% of GDP per year", "0.5% allocation × 90% execution."],
            ["Productive investment", f"{central['productive']:.2f}% of GDP per year", "Executed spending discounted for a 10% overrun."],
            ["Annual GDP effect after lag", f"{central['annual_impact']:.2f}% of GDP", "Direct multiplier plus crowd-in effect."],
            ["Five-year cumulative GDP effect", f"{central['cumulative_gdp']:.2f}%", "Sum of annual effects realised within the horizon."],
            ["GDP per ₹1 announced CapEx", f"₹{central['gdp_per_rupee']:.2f}", "Modelled cumulative GDP within five years divided by five annual allocations."],
            ["Year-five debt-ratio change", f"{central['debt_change']:+.2f} percentage points", "Difference from the dynamic baseline after borrowing, interest, growth and revenue feedback."],
        ],
        widths=[2300, 2200, 4500],
    )
    doc.add_heading("Preset interpretation", 2)
    doc.table(
        ["Preset", "Economic narrative", "Use"],
        [
            ["Conservative", "Lower execution and multiplier, two-year lag, mild crowding out, higher overruns, full borrowing and weaker revenue feedback.", "Stress test for weak delivery and expensive financing."],
            ["Central", "High but imperfect execution, unit multiplier, one-year lag, modest crowd-in and partial borrowing.", "Neutral working case, not an official forecast."],
            ["Optimistic", "Full execution, higher multiplier, rapid implementation, stronger crowd-in, lower overrun and financing cost.", "Upper-bound transmission scenario."],
        ],
        widths=[1700, 5200, 2000],
    )
    doc.add_heading("Model interpretation and failure modes", 2)
    for item in [
        "A negative year-five debt change means the modelled denominator and revenue effects more than offset the incremental debt addition relative to the dynamic baseline. It does not mean the absolute debt stock falls.",
        "A high multiplier can mechanically improve both GDP per rupee and debt/GDP. Analysts should therefore report the assumed multiplier beside every result.",
        "Lower execution reduces both productive output and borrowing. Higher cost overruns reduce productive output without reducing executed spending.",
        "The model treats each annual impulse symmetrically and does not model depreciation, sector-specific multipliers, project gestation distributions, inflation composition, monetary-policy responses or state-government feedback.",
        "Cumulative GDP is an accounting sum of annual level effects inside the selected horizon. It is not a present-value welfare calculation.",
        "The dynamic baseline includes the primary balance and r−g arithmetic, but it still omits explicit stock-flow adjustments, maturity structure, valuation effects and endogenous monetary or fiscal responses.",
        "The uncertainty view uses 1,200 deterministic seeded draws. The sensitivity tornado moves one registered range at a time; the clickable frontier maps CapEx and multiplier combinations; the one-year backtest reports MAE and RMSE against observed debt.",
    ]:
        doc.add_bullet(item)

    doc.add_heading("13. How to interpret the entire story", 1)
    steps = [
        "Start with execution, not the headline budget. Confirm that the policy impulse was both large relative to GDP and substantially delivered.",
        "Check allocation and physical delivery separately. A rising Roads or Railways BE is an input; kilometres are selected outputs; neither establishes quality-adjusted capital services.",
        "Read absolute market performance before relative performance. Then ask whether the CapEx-sensitive sector beat Nifty 50 and whether the pattern differs from FMCG.",
        "Use both timing directions. A strong market-leads result may indicate anticipation; a forward result is more consistent with later response but remains non-causal.",
        "Inspect scatter points, the fitted line, n and pandemic sensitivity. Do not report a coefficient without its timing window and sample size.",
        "Check corporate revenue, earnings, CapEx and PPE. A market re-rating unsupported by fundamentals is a weaker transmission story.",
        "Move to private GFCF, utilisation and capital-goods IIP. This is where expectations must become realised productive activity.",
        "Finish with fiscal capacity. Compare growth evidence with debt, primary balance and interest pressure rather than treating CapEx as costless.",
        "Use the scenario lab only after the historical evidence. Vary execution, multiplier and financing assumptions to identify which assumptions drive the conclusion.",
    ]
    for index, text in enumerate(steps, start=1):
        doc.add_number(index, text)

    doc.add_heading("14. Limitations and research extensions", 1)
    doc.table(
        ["Limitation", "Why it matters", "Best next extension"],
        [
            ["Small annual timing sample", "Coefficients can change sharply when one fiscal year moves.", "Extend history where index definitions permit; report bootstrap or randomisation uncertainty without data-mining lags."],
            ["Nominal CapEx", "Inflation can mimic stronger real investment.", "Register a defensible government-investment deflator and publish both nominal and real growth."],
            ["Budget rather than ministry actuals", "Allocation does not prove sector execution.", "Build comparable Roads and Railways actual/revised capital series by budget vintage."],
            ["Output quantity without quality", "Kilometres ignore lanes, reliability and usage.", "Add lane-km, freight capacity, travel-time or utilisation outcomes with consistent definitions."],
            ["Short private GFCF history", "Crowding-in inference is underpowered.", "Use a longer compatible national-accounts vintage or clearly model a structural break."],
            ["Corporate-provider comparability", "Statement taxonomy and coverage can change.", "Replace or validate provider fields with company annual reports and document restatements."],
            ["No causal design", "Common macro shocks remain plausible explanations.", "Pre-register a panel, event-study, project-level or instrumental-variable strategy only when treatment and counterfactual data support it."],
            ["Conditional uncertainty", "Registered ranges are analyst assumptions, not estimated sampling distributions.", "Add parameter provenance and correlated macro shocks before considering a formal forecast."],
        ],
        widths=[2100, 3400, 3500],
        font_size=15,
    )

    doc.add_heading("15. Source map", 1)
    source_rows = []
    seen: set[tuple[str, str]] = set()
    for payload in (execution, allocation, delivery, production, private, fiscal, corporate):
        source = payload["metadata"].get("source", [])
        if isinstance(source, str):
            source = [{"name": source}]
        for item in source:
            name = item.get("name", "Unlabelled source")
            url = item.get("url", "")
            key = (name, url)
            if key not in seen:
                seen.add(key)
                source_rows.append([name, url or "Recorded source metadata; no URL in this chart contract"])
    source_rows.append([str(sectors["metadata"].get("source")), "https://www.niftyindices.com/reports/historical-data"])
    doc.table(["Source", "Official location or provenance note"], source_rows, widths=[3800, 5200], font_size=14)

    doc.add_heading("16. Glossary", 1)
    doc.table(
        ["Term", "Meaning"],
        [
            ["BE / RE", "Original Budget Estimate / in-year Revised Estimate."],
            ["CapEx", "Capital expenditure intended to create or acquire assets or reduce liabilities under the applicable fiscal classification."],
            ["GFCF", "Gross fixed capital formation: acquisition less disposal of fixed assets, before depreciation."],
            ["IIP", "Index of Industrial Production."],
            ["TRI", "Total-return index, including reinvested distributions."],
            ["Relative wealth", "Cumulative sector TRI performance divided by cumulative benchmark TRI performance."],
            ["Crowding in / out", "Private investment increases / decreases in response to public investment or its financing and macro effects."],
            ["Fiscal multiplier", "Change in output associated with one unit of fiscal impulse under specified conditions."],
            ["Primary balance", "Fiscal balance before interest payments; negative values here indicate a primary deficit."],
            ["Interest-growth differential", "Difference between the effective interest rate and nominal GDP growth, central to debt dynamics."],
            ["Percentage point", "Arithmetic difference between two percentages; distinct from percentage growth."],
        ],
        widths=[2500, 6500],
    )
    doc.add_paragraph(
        "End of economic and methodology guide.",
        align="center",
        space_before=360,
        runs=[doc.run("End of economic and methodology guide.", italic=True, color="64748B")],
    )
    doc.save(ECONOMIC_GUIDE)


def artifact_inventory() -> list[list[str]]:
    rows = []
    schemas = {
        "execution": "dated_multi_series",
        "allocation": "dated_multi_series",
        "delivery": "dated_multi_series",
        "production": "dated_multi_series",
        "sectors": "market_performance",
        "correlations": "dated_multi_series",
        "private": "dated_multi_series",
        "fiscal": "dated_multi_series",
        "summary": "capex_analysis_summary",
        "corporate": "dated_multi_series",
        "quality": "dated_multi_series",
        "states": "dated_multi_series",
        "crowding_in": "dated_multi_series",
    }
    for key, relative in OUTPUTS.items():
        payload = load_artifact(key)
        if "series" in payload:
            dimensions = f"{len(payload['series'])} series / {sum(len(x['values']) for x in payload['series'].values())} observations"
            coverage = f"{payload['metadata'].get('start_date')} → {payload['metadata'].get('end_date')}"
        elif "markets" in payload:
            dimensions = f"{len(payload['markets'])} markets / {sum(len(x['series']) for x in payload['markets'].values())} observations"
            coverage = f"{payload['metadata'].get('start_date')} → {payload['metadata'].get('end_date')}"
        else:
            dimensions = f"{len(payload.get('hypotheses', []))} hypotheses"
            coverage = "Rule-generated at build time"
        rows.append([key, relative, schemas[key], dimensions, coverage])
    return rows


def build_technical_guide() -> None:
    doc = ooxml.DocxBuilder()
    configure_package(
        "India’s Public CapEx Transmission: Technical Guide",
        "CapEx transmission  |  Technical implementation guide",
    )
    title_page(
        doc,
        "India’s Public CapEx Transmission",
        "Technical guide to sources, ETL, contracts, frontend integration, verification and deployment",
        "This document is for data engineers, software engineers, maintainers and technical reviewers. It maps each research stage to source acquisition, transformation code, output contracts, public paths, frontend adapters and operational checks.",
    )
    add_toc(doc)

    doc.add_heading("1. System overview", 1)
    doc.add_paragraph(
        "The CapEx research lens is a static, reproducible analytical product. Python jobs acquire or consume "
        "source data, preserve immutable raw evidence, transform observations without I/O, validate the complete "
        "artifact set and publish processed plus browser-facing JSON. The generated "
        "catalogue maps stable asset IDs to schemas and presentation components. "
        "React Query loads static JSON at runtime; runtime guards and component-schema mappings prevent an "
        "artifact from reaching an incompatible visualisation."
    )
    doc.add_code(
        "Official source or data/raw replay → typed source models → typed calculated metrics → final payload builders → complete-set validation → per-file atomic processed/public JSON → catalogue → runtime guard → specialised React component"
    )
    doc.add_callout(
        "Deployment model",
        "There is no application API and no deployment-platform configuration in the repository. The deployable unit is frontend/dist, produced by Vite. Any static host can serve it if deep routes fall back to index.html and /data assets are served with the build.",
        color="1F4E78",
        shade="EAF2F8",
    )

    doc.add_heading("2. Repository responsibility map", 1)
    doc.table(
        ["Location", "CapEx responsibility", "Important invariant"],
        [
            ["scripts/config/capex_analysis.py", "Frozen market definitions, benchmark/control roles, corporate basket, lags and output paths.", "Machine keys and research scope are declared before transforms."],
            ["scripts/build_capex_pipeline.py", "Sole full and targeted ETL executable.", "Every payload validates before target selection and the first processed or public write."],
            ["scripts/extractors/capex_sources.py", "Live acquisition and immutable-landed-source replay.", "Extraction returns typed source containers; raw evidence is independent of publication."],
            ["scripts/extractors/delivery_reference.py", "Validation and typed extraction of transcribed allocation, delivery and IIP observations.", "Reference observations cross the same extraction boundary as downloaded sources."],
            ["sources/capex_delivery_reference.json", "Version-controlled transcription of official annual tables awaiting automated document parsers.", "Data is source input, never executable builder code."],
            ["scripts/models/capex_sources.py", "Provider-response and cross-layer source containers.", "Transforms depend on shared models, never extractor implementations."],
            ["scripts/models/capex_metrics.py", "GovernmentMetrics, PrivateMetrics and FiscalMetrics contracts.", "Intermediate calculations carry CanonicalRecord tuples and provenance, never JSON-shaped payload dictionaries."],
            ["scripts/transforms/capex_metrics.py", "Explicit construction and validation of typed structural metrics.", "Government metrics feed private metrics directly as records; no intermediate JSON is constructed."],
            ["scripts/builders/capex_artifacts.py", "Pure dependency ordering and complete artifact assembly.", "No network, processed-file reads or publication side effects."],
            ["scripts/extractors/nifty_indices.py", "Official Nifty TRI sessions, annual request windows and immutable JSON landing.", "Every market must return observations; one common sample is enforced later."],
            ["scripts/extractors/corporate_fundamentals.py", "Company statement extraction and raw landing.", "The basket is frozen; provider field fallbacks are explicit."],
            ["scripts/builders/fiscal_outputs.py", "Final execution and fiscal-sustainability payloads.", "Each public function constructs exactly one registered output."],
            ["scripts/builders/market_outputs.py", "Final sector-performance and correlation payloads.", "Correlation support estimates are returned in a typed result for the summary builder."],
            ["scripts/builders/real_economy_outputs.py", "Final allocation, delivery, production, private-response and corporate payloads.", "Each public function constructs exactly one registered output."],
            ["scripts/builders/evaluation_outputs.py", "Final quality, state, crowding-in and summary payloads.", "Each public function constructs exactly one registered output."],
            ["scripts/transforms/capex_depth.py", "Project blocks, state panel, fixed effects and crowding-in gates.", "Causal language is prohibited; sample eligibility is explicit."],
            ["scripts/transforms/capex_analysis.py", "Market wealth, lead/lag alignment, correlations and deterministic hypotheses.", "No causal claim; fixed windows; missing pairs are not imputed."],
            ["scripts/transforms/corporate_fundamentals.py", "Within-company growth and group medians.", "Aggregate after company-level growth."],
            ["scripts/validators/", "Draft 2020-12 schema validation and semantic evidence checks.", "Reject a candidate before replacement."],
            ["scripts/exporters/json_export.py", "Strict JSON and per-file atomic filesystem replacement.", "No NaN or partially written JSON file reaches either output directory."],
            ["scripts/sync_focused_catalogue.py", "Asset definitions, stage order, views and adapter names.", "Catalogue is the presentation contract."],
            ["frontend/src/data/", "TypeScript payload types, static client and runtime guards.", "Declared schema must match detected payload and component."],
            ["frontend/src/components/", "General and specialised CapEx visualisations.", "Research statistics are not recomputed except interactive scenario arithmetic and chart-only fitted lines."],
            ["frontend/public/data/", "Browser-facing artifacts and schemas.", "Published copies match validated processed artifacts."],
            ["tests/", "CapEx transforms, source parser contracts and publication-boundary tests.", "Regression tests protect registered windows, source semantics and CapEx-only public routing."],
        ],
        widths=[2500, 4300, 2200],
        font_size=15,
    )

    doc.add_heading("3. Source inventory and acquisition", 1)
    doc.table(
        ["Source", "Data used", "Acquisition path", "Raw/provenance behaviour"],
        [
            ["Union Budget — Budget at a Glance", "Central CapEx actual, BE, RE, total expenditure and execution inputs.", "capex_sources acquires and parses every edition from 2018 onward.", "PDFs are checksum-landed directly under data/raw/union-budget/."],
            ["Union Budget — Expenditure Profile Statement 3", "Roads and Railways central-budget capital BE.", "delivery_reference extracts a version-controlled transcription of four reconciled statement vintages.", "Source URLs, retrieval times and observations live in sources/capex_delivery_reference.json."],
            ["MoRTH Annual Report", "National-highway kilometres constructed.", "delivery_reference extracts the transcribed official fiscal-year series.", "Metadata and observations live in the tracked reference source."],
            ["Indian Railways Annual Report", "Route kilometres electrified.", "delivery_reference extracts the transcribed official fiscal-year series.", "Metadata and observations live in the tracked reference source."],
            ["Nifty Indices", "Five daily total-return indices.", "Session GET then provider POST in annual windows; responses normalised into pandas series.", "Each index is landed under data/raw/nifty-indices/<retrieval-date>/ with a content hash."],
            ["Yahoo Finance statements", "Revenue, EBITDA, CapEx, net PPE, debt, EBIT, assets and current liabilities for ten firms.", "yfinance annual statement tables.", "Each company’s extracted observations are checksum-landed under data/raw/corporate-fundamentals/."],
            ["MoSPI national accounts", "Private corporate GFCF, total GFCF and nominal GDP.", "NationalAccountsExtractor in the extraction layer.", "Base-year-compatible series and statuses are preserved."],
            ["RBI OBICUS", "Unadjusted manufacturing capacity utilisation.", "Stable publication ID 23808; HTML parser in the extraction layer.", "Quarterly status and source metadata are retained."],
            ["RBI fiscal tables", "Debt/GDP, primary deficit, revenue, interest and expenditure ratios.", "Stable publication IDs 23413 and 23410.", "Actual, revised and budget status remain attached."],
            ["RBI Handbook / NSO IIP", "Fiscal-year capital-goods IIP.", "delivery_reference extracts transcribed official Table 30 values.", "Source URL, retrieval time and observations live in the tracked reference source."],
            ["RBI Handbook 2022–23 / MoSPI", "Central-sector project status and cost overrun, 2009–2023.", "Stable archived publication IDs 21841 and 21842 parsed as sector/year blocks.", "HTML is checksum-landed under data/raw/rbi-handbook/<date>/."],
            ["RBI Handbook of Statistics on Indian States", "Current/constant GSDP and state capital outlay.", "Stable publication IDs 23470, 23471 and 23623 parsed as state/year matrices.", "Actual/revised/budget labels are retained; only actual outlay enters the panel."],
        ],
        widths=[2200, 2600, 2700, 1700],
        font_size=14,
    )
    doc.add_heading("Manual-source acquisition", 2)
    doc.add_paragraph(
        "Statement 3, physical-delivery and capital-goods IIP observations are manually transcribed from official "
        "documents into sources/capex_delivery_reference.json until automated document parsers exist. "
        "extract_delivery_sources reads, checksums and validates that file during Extract and returns typed "
        "DeliverySources. The builder receives only those typed values. Manual acquisition changes how a source "
        "is obtained, not the abstract pipeline or the extraction/transform boundary."
    )

    doc.add_heading("4. Canonical models and period semantics", 1)
    doc.add_heading("Shared canonical record", 2)
    doc.table(
        ["Field", "Type/meaning", "CapEx use"],
        [
            ["date", "Normalised date", "Fiscal years normally use 31 March; market observations use provider dates before monthly sampling."],
            ["entity", "Provider-neutral identifier", "IND for national series; company and market keys use frozen registry keys."],
            ["indicator", "Stable machine key", "Links registry definition, transform and published series."],
            ["value", "Finite float or null", "NaN and infinity are prohibited at serialisation."],
            ["unit / frequency", "Explicit measurement metadata", "Prevents unsafe joins and controls display formatting."],
            ["status", "actual, provisional, revised, estimate or budget", "Distinguishes out-turns from fiscal plans and model starting points."],
            ["period_label", "Human-readable FY/reporting label", "Prevents 31 March dates from being read as calendar-year observations."],
            ["source_url / retrieved_at / vintage", "Provenance", "Supports audit of changing institutional publications."],
            ["period_start / period_end", "Inclusive non-calendar bounds", "Used by fiscal-period-safe structural joins."],
        ],
        widths=[1900, 2900, 4200],
        font_size=15,
    )
    doc.add_paragraph(
        "The shared FiscalPeriod model represents an Indian fiscal year from 1 April through 31 March. "
        "ObservationStatus is an enum, so budget and estimate cannot be silently treated as actual. The CapEx "
        "orchestrator passes typed source containers from models/capex_sources.py into builders. Corporate "
        "extraction uses an immutable CorporateFundamental model before aggregation."
    )

    doc.add_heading("5. Artifact contracts and inventory", 1)
    doc.table(
        ["Key", "Processed/public path", "Schema", "Dimensions", "Coverage"],
        artifact_inventory(),
        widths=[1300, 2600, 1900, 1800, 1400],
        font_size=13,
    )
    doc.add_heading("dated_multi_series", 2)
    doc.add_paragraph(
        "The metadata object requires generated_at, source, frequency, true start/end dates, indicator_code, "
        "label, default_unit, series_order and is_derived. Each named series requires label, entity, unit and "
        "values. Values require an ISO date and numeric-or-null value; status and period_label are optional but "
        "used extensively. additionalProperties is false at the payload and series levels, while metadata allows "
        "documented analytical additions such as correlation_estimates, company_coverage and transmission_evidence."
    )
    doc.add_heading("market_performance", 2)
    doc.add_paragraph(
        "The market contract carries source/start/end metadata and a market mapping. Each observation can contain "
        "price, independently normalised value, total or excess return fields, relative wealth, drawdown and rolling "
        "volatility. The CapEx bundle retains both raw_return and benchmark-excess return so the broad Nifty 50 test "
        "can use raw market performance while target sectors use excess performance."
    )
    doc.add_heading("capex_analysis_summary", 2)
    doc.add_paragraph(
        "The summary contract requires a research question, classification method and four structured hypotheses. "
        "Each hypothesis carries a stable key, claim, status, interpretation and caveat. The artifact is published "
        "and schema-validated but is loaded directly by CapexVerdict rather than through a catalogue asset."
    )
    doc.add_heading("Catalogue presentation contract", 2)
    doc.add_paragraph(
        "Each view binds an asset_id to a component, chart type, x-axis, default visible keys, value format, "
        "controls and source/methodology flags. The catalogue schema enumerates specialised components including "
        "capex-correlation, corporate-fundamentals, fiscal-bridge, investment-quality, crowding-in, state-capex-evaluation and capex-scenario-lab."
    )

    doc.add_heading("6. End-to-end ETL by artifact", 1)
    doc.table(
        ["Output", "Inputs", "Core transform", "Validation and consumer"],
        [
            ["capex-execution.json", "GovernmentMetrics canonical records", "Scope from FY2017–18; retain ratios/vintages; derive nominal growth; build JSON once", "dated_multi_series → general line charts"],
            ["sector-capex-allocation.json", "Typed Statement 3 observations from DeliverySources", "Map FY label to 31 March; budget status; separate Roads/Railways series", "dated_multi_series → allocation line view"],
            ["physical-delivery.json", "Typed MoRTH and Railways observations from DeliverySources", "Map annual km outputs; actual status", "dated_multi_series → physical-delivery line view"],
            ["capital-goods-production.json", "Typed RBI/NSO Table 30 observations from DeliverySources", "Map fiscal average IIP; preserve pandemic observation", "dated_multi_series → 2D production view"],
            ["sector-performance.json", "Official daily TRI matrix", "Common-date drop; month-end sampling; total/excess returns; rebasing; risk summaries", "market_performance → ChartView"],
            ["capex-sector-correlations.json", "GovernmentMetrics, PrivateMetrics and market calculations", "Fixed forward/reverse windows; pair by fiscal end; Pearson/Spearman; pandemic sensitivity", "dated_multi_series metadata → CapexCorrelationView"],
            ["corporate-fundamentals.json", "Ten CorporateFundamental histories", "Within-company growth; unweighted group median; coverage metadata", "dated_multi_series → CorporateFundamentalsView"],
            ["private-investment-response.json", "PrivateMetrics canonical records", "Scope GFCF, utilisation and one-year public-CapEx lag; build JSON once", "dated_multi_series → general line chart"],
            ["investment-quality.json", "RBI/MoSPI project status and cost tables", "Parse sector blocks; derive schedule, delay and cost-overrun shares; retain sector histories", "dated_multi_series metadata → InvestmentQualityView"],
            ["crowding-in-evidence.json", "GovernmentMetrics, PrivateMetrics and typed IIP source observations", "Fixed 0–3 year alignment; Pearson/Spearman; eight-observation eligibility gate", "dated_multi_series metadata → CrowdingInView"],
            ["state-capex-evaluation.json", "RBI state outlay and current/constant GSDP", "Scale outlay; pair next-year growth; two-way demean; state-clustered SE", "dated_multi_series metadata → StateCapexEvaluationView"],
            ["fiscal-sustainability.json", "FiscalMetrics plus GovernmentMetrics", "Join typed records; add CapEx share and allocation ratio; attach verdict chain; build JSON once", "dated_multi_series → FiscalBridgeView and ScenarioLab"],
            ["analysis-summary.json", "GovernmentMetrics, PrivateMetrics, FiscalMetrics and correlation estimates", "Deterministic directional classification; reverse leads and Nifty 50 excluded from H2", "capex_analysis_summary → CapexVerdict"],
        ],
        widths=[2300, 2300, 3100, 1300],
        font_size=13,
    )

    doc.add_heading("7. Core transformation algorithms", 1)
    doc.add_heading("Market alignment", 2)
    doc.add_number(1, "Require Nifty 50, every target and FMCG to contain non-empty price histories.")
    doc.add_number(2, "Sort by date, retain only rows where every required market has a value, and select the last provider observation in each calendar month.")
    doc.add_number(3, "Compute monthly total returns with no forward filling.")
    doc.add_number(4, "For target series, subtract Nifty 50 monthly returns to create excess-return observations.")
    doc.add_number(5, "Construct relative wealth by compounding the ratio of sector and benchmark gross returns.")
    doc.add_number(6, "Publish independent rebased TRI levels for the FMCG comparison and stable summary statistics.")
    doc.add_heading("Lead/lag alignment", 2)
    doc.add_paragraph(
        "capex_growth_series derives annual percentage changes from actual CapEx. For every fiscal end and fixed "
        "market window, the transform selects monthly returns strictly inside the registered boundaries, requires "
        "at least nine monthly observations, compounds them, and records a value at the CapEx fiscal-end date. "
        "Correlation pairs are assembled only from complete matching dates. Fiscal ends 2021 and 2022 are removed "
        "only in the registered pandemic sensitivity."
    )
    doc.add_heading("Corporate aggregation", 2)
    doc.add_paragraph(
        "Records are sorted by company and date. pandas groupby.pct_change with fill_method=None calculates each "
        "company’s level growth. Infinite results are replaced by missing values. The median is then taken across "
        "available firms within the frozen group and reporting year. ROCE is a level proxy and is therefore not "
        "differenced before the median."
    )
    doc.add_heading("Fiscal bridge", 2)
    doc.add_paragraph(
        "The actual CapEx expenditure-share CanonicalRecord in GovernmentMetrics is joined by exact fiscal-end "
        "date to the interest-expenditure CanonicalRecord in FiscalMetrics. The allocation ratio divides "
        "the two shares; a zero or missing interest denominator is omitted. Observation status is conservatively "
        "propagated from the non-actual input when applicable. Only then does build_fiscal_sustainability_payload "
        "construct the final JSON dictionary."
    )

    doc.add_heading("8. Full pipeline and analysis orchestration", 1)
    doc.add_heading("Central ETL command", 2)
    doc.add_code("PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py")
    doc.add_paragraph(
        "The central orchestrator runs one visible sequence: Extract, Transform, Validate, Load and Verify. "
        "Validation and verification are control gates around ETL rather than additional data layers. The central "
        "script is the only analytical executable for both full and targeted runs."
    )
    doc.add_heading("Step 1 — Extract", 2)
    doc.add_paragraph(
        "run_pipeline selects live or offline acquisition. Live mode calls acquire_capex_sources with data/raw as "
        "the landing root. Provider-specific extractors download source documents, retain checksum- or date-based "
        "filenames, parse the relevant tables and return StructuralSources, AnalysisSources and DepthSources. "
        "extract_delivery_sources separately parses the tracked sources/capex_delivery_reference.json into "
        "DeliverySources. All four containers are placed inside one CapexSources object before Transform begins. "
        "Offline mode calls load_landed_capex_sources, selects the latest registered files "
        "already under data/raw and reruns the same PDF, HTML and JSON parsers in place. Raw files are evidence: "
        "they remain available if a later transform or validation step fails."
    )
    doc.add_heading("Step 2 — Transform", 2)
    doc.add_paragraph(
        "build_capex_artifacts receives CapexSources and performs no network or filesystem access. It directly "
        "calls calculate_government_metrics, calculate_private_metrics and calculate_fiscal_metrics. These return "
        "GovernmentMetrics, PrivateMetrics and FiscalMetrics: frozen dataclasses containing CanonicalRecord tuples "
        "and provenance. calculate_private_metrics reads GovernmentMetrics records to build the lagged public-CapEx "
        "record. No intermediate metadata/series dictionary exists. build_capex_artifacts then directly calls all "
        "thirteen final builders: execution, allocation, delivery, production, sectors, correlations, private, "
        "summary, fiscal, corporate, quality, states and crowding-in. Downstream correlation, summary, fiscal-bridge and crowding-in calculations consume "
        "typed metrics or typed source observations directly. "
        "build_capex_artifacts returns exactly thirteen final-output dictionaries and performs no I/O."
    )
    doc.add_heading("Step 3 — Validate before loading", 2)
    doc.add_paragraph(
        "_validate_all_artifacts first requires exactly the thirteen keys in OUTPUTS. _artifact_entries assigns "
        "each final payload its registered relative path and schema. "
        "validate_payload checks every complete dictionary against its Draft 2020-12 schema. json.dumps then performs "
        "a strict serialisation preflight with allow_nan=False. If any payload fails, no processed or public JSON is "
        "written; newly acquired immutable raw evidence is retained. Only after all thirteen pass does "
        "_select_artifact_entries apply --target."
    )
    doc.add_heading("Step 4 — Load", 2)
    doc.add_paragraph(
        "With --target all, _publish_artifacts writes all thirteen validated payloads under data/processed and "
        "writes identical copies under frontend/public/data. An output target writes one processed file and its "
        "public copy. write_json_atomic "
        "serialises to a temporary sibling file, flushes it, calls fsync and replaces the destination with os.replace. "
        "Each JSON file is individually atomic, but a multi-file run is not a transaction and has no cross-file rollback."
    )
    doc.add_heading("Step 5 — Verify after loading", 2)
    doc.add_paragraph(
        "_verify_written_artifacts reopens every selected processed file and validates it again. For selected final "
        "outputs it also compares the processed SHA-256 digest with the browser-facing copy. A mismatch or missing "
        "file fails the run visibly. Verification detects publication problems; it does not roll earlier writes back."
    )
    doc.add_heading("Layer boundary", 2)
    doc.add_paragraph(
        "extractors/capex_sources.py contains network and landed-file parsing. models/capex_sources.py defines "
        "the typed values crossing into the calculation layer. models/capex_metrics.py defines the typed calculation "
        "boundary and transforms/capex_metrics.py constructs those metrics. builders/fiscal_outputs.py, "
        "market_outputs.py, real_economy_outputs.py and evaluation_outputs.py each expose one function per final "
        "output. capex_artifacts.py calls all thirteen functions explicitly. "
        "build_capex_pipeline.py owns validation and publication; json_export.py owns one-file atomic replacement."
    )
    doc.add_heading("Explicit call-graph rule", 2)
    doc.add_paragraph(
        "Pipeline orchestration functions accept data and configuration values, not behavior. run_pipeline calls "
        "acquire_capex_sources or load_landed_capex_sources by name, then directly calls build_capex_artifacts, "
        "_validate_all_artifacts, _select_artifact_entries, _publish_artifacts and _verify_written_artifacts. "
        "_publish_artifacts directly calls "
        "write_json_atomic. Tests exercise these concrete stages with artifact data rather than injecting replacement "
        "functions. The production Python contains no lambdas, Callable dependencies or callback configuration."
    )
    doc.add_heading("Immutable-source replay", 2)
    doc.add_code("PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py --offline")
    doc.add_paragraph(
        "Offline mode selects the latest immutable file for every registered source under data/raw, reads it in "
        "place, reruns the production parsers and executes the same transform, validation, load and verification "
        "path. It does not treat processed JSON as source input."
    )
    doc.add_heading("Targeted execution", 2)
    doc.add_code("PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py --target output:execution")
    doc.add_code("PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py --offline --target output:quality")
    doc.add_paragraph(
        "The only target namespace is output:<key>; the default is all. Target selection does not create "
        "a shorter or different calculation path: every source dependency is acquired, the complete artifact graph "
        "is built, and all thirteen payloads validate. It limits only the Load and Verify steps. This preserves one "
        "call graph and prevents existing processed JSON from becoming a hidden transformation input."
    )

    doc.add_heading("9. Validation-first, per-file atomic publication", 1)
    doc.add_number(1, "Raw acquisition writes immutable source evidence directly under data/raw.")
    doc.add_number(2, "All transforms and payload assembly finish in memory before output publication begins.")
    doc.add_number(3, "The builder must return exactly all thirteen registered final CapEx keys.")
    doc.add_number(4, "Every payload is schema-validated and strictly serialisation-tested with allow_nan=False.")
    doc.add_number(5, "Each processed and public JSON uses temporary-file, fsync and os.replace publication.")
    doc.add_number(6, "There is no backup tree or run-level rollback; a failure between files may leave a mixed output generation.")
    doc.add_number(7, "The operator reruns the complete idempotent ETL after correcting any publication failure.")
    doc.add_number(8, "Every final processed/public pair is revalidated and checked for equal SHA-256 content.")
    doc.add_paragraph(
        "This design deliberately favours an understandable validation gate and safe individual files over a "
        "filesystem approximation of a database transaction. Full and targeted publication both use the same "
        "write_json_atomic implementation in the central ETL."
    )

    doc.add_heading("10. Catalogue and frontend integration", 1)
    doc.add_heading("Catalogue generation", 2)
    doc.add_paragraph(
        "sync_focused_catalogue removes any previous generated capex-transmission section, registers twelve chart "
        "assets, builds eleven ordered stage indicators and validates the completed catalogue. The summary "
        "artifact is intentionally loaded by the CapexVerdict component rather than counted as a chart asset."
    )
    doc.table(
        ["Component", "Schema", "Responsibility"],
        [
            ["ChartView", "dated_multi_series or market_performance", "General line rendering, stable series colours, toggles, tooltips and legends."],
            ["CapexCorrelationView", "dated_multi_series", "Timing controls, heatmap, detailed and mini scatter plots, coefficients and fitted lines."],
            ["CorporateFundamentalsView", "dated_multi_series", "Metric tabs, group-median bars and basket coverage."],
            ["FiscalBridgeView", "dated_multi_series", "Allocation ratio, evidence chain and fiscal quadrant scatter."],
            ["InvestmentQualityView", "dated_multi_series", "Sector/year delivery trends and latest-year delay/overrun map."],
            ["CrowdingInView", "dated_multi_series", "Outcome/lag selection, sample gates, scatter and fitted line."],
            ["StateCapexEvaluationView", "dated_multi_series", "State/year filtering and fixed-effects result interpretation."],
            ["CapexScenarioLab", "dated_multi_series", "Dynamic baseline, Monte Carlo paths, tornado, frontier, backtest and KPIs."],
            ["CapexVerdict", "capex_analysis_summary", "Directly loads and renders deterministic hypothesis statuses."],
            ["SourcePanel", "Payload metadata", "Displays source and methodology provenance beside every chart."],
        ],
        widths=[2400, 2200, 4400],
        font_size=15,
    )
    doc.add_heading("Runtime loading", 2)
    doc.add_paragraph(
        "useIndicatorData builds a React Query key from data_path and asset version, then loadStaticAsset fetches "
        "the browser JSON. detectSchema inspects structural discriminators. assertPayload verifies the catalogue’s "
        "declared schema, and assertAdapterMatchesSchema verifies the selected component. This is a runtime defence "
        "in addition to TypeScript and build-time AJV validation."
    )
    doc.add_heading("Stable colours and view state", 2)
    doc.add_paragraph(
        "General line colours use the series’ position in the full registered key list, not the current visible "
        "list. A series therefore retains its colour after other lines are hidden and restored. ChartView is keyed "
        "by view ID so switching between allocation and delivery creates clean state rather than leaking visible "
        "keys across incompatible assets."
    )

    doc.add_heading("11. Scenario-lab implementation", 1)
    doc.add_paragraph(
        "CapexScenarioLab remains a frontend calculation so analysts receive instant feedback without server state. "
        "Presets are immutable parameter objects; moving a range input marks the state Custom. useMemo recalculates "
        "the deterministic path, 1,200 fixed-seed draws, break-even multiplier, sensitivity ranking and historical "
        "one-step backtest whenever an assumption or debt baseline changes."
    )
    doc.add_code("delivered = capex × execution")
    doc.add_code("productive = delivered / (1 + overrun)")
    doc.add_code("annualImpact = productive × (multiplier + crowdIn)")
    doc.add_code("baselineDebtₜ = baselineDebtₜ₋₁ × (1+interest)/(1+growth) − primaryBalance")
    doc.add_code("incrementalDebtₜ = incrementalDebtₜ₋₁ × (1+interest)/(1+growth) + delivered×borrowingShare − benefitₜ×revenueShare")
    doc.add_code("scenarioDebtₜ = (baselineDebtₜ + incrementalDebtₜ) / (1 + cumulativeGDPₜ/100)")
    doc.add_paragraph(
        "latestSettled filters out budget and estimate statuses before selecting the starting debt observation. "
        "The component does not mutate or publish data. It renders a conditional scenario against a dynamic debt "
        "baseline. Parameter values and results disappear on page reload because no persistence is intended."
    )
    doc.add_callout(
        "Model versioning recommendation",
        "Before the model is used in a formal published forecast, move preset/range definitions and formula-version metadata into a validated scenario-model contract, add unit tests around a shared pure calculation module, estimate correlated parameter distributions, and expose a downloadable assumption/result record.",
        color="A33D4A",
        shade="FFF1F2",
    )

    doc.add_heading("12. Testing and verification", 1)
    doc.table(
        ["Check", "Command", "What it protects"],
        [
            ["Backend suite", "PYTHONPATH=scripts venv/bin/python -m unittest discover -s tests -p 'test_*.py'", "Tests cover CapEx transforms, registered lag windows, source parsers, schemas and the CapEx-only publication boundary."],
            ["Static-data validation", "cd frontend && npm run validate:data", "Catalogue schema, all referenced assets, adapter/schema compatibility, metadata coverage and duplicates."],
            ["Type checking", "cd frontend && npx tsc --noEmit", "TypeScript component and payload compatibility."],
            ["Lint", "cd frontend && npm run lint", "Frontend correctness and dead-code checks."],
            ["Production build", "cd frontend && npm run build", "Runs data validation and creates optimised frontend/dist."],
            ["Whitespace/conflict check", "git diff --check", "Trailing whitespace and unresolved patch formatting."],
        ],
        widths=[1800, 4400, 2800],
        font_size=14,
    )
    doc.add_paragraph(
        "At generation time all 35 backend tests pass, 12 static assets and one catalogue section validate, "
        "TypeScript and lint pass, and the Vite production build succeeds. The remaining notice is a bundle-size "
        "warning: the main JavaScript chunk is approximately 653 KB minified and 196 KB gzip."
    )

    doc.add_heading("13. Build and deployment runbook", 1)
    doc.add_heading("Prerequisites", 2)
    for item in [
        "Python environment with dependencies from requirements/requirements.txt.",
        "Node dependencies installed in frontend/.",
        "pdftotext available for the broader official-PDF extraction pipeline.",
        "Network access for live mode, or a complete immutable data/raw landing for --offline mode.",
    ]:
        doc.add_bullet(item)
    doc.add_heading("Recommended full refresh", 2)
    doc.add_code("PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py")
    doc.add_code("PYTHONPATH=scripts venv/bin/python scripts/sync_focused_catalogue.py")
    doc.add_code("cd frontend && npm run validate:data && npx tsc --noEmit && npm run lint && npm run build")
    doc.add_paragraph(
        "The pipeline command performs live acquisition by default. Use --offline for a deterministic replay of "
        "the immutable raw landing. Both modes use the same pure builders, validation and publication functions. "
        "Catalogue synchronisation updates versions and availability after successful publication."
    )
    doc.add_heading("Static deployment", 2)
    doc.add_number(1, "Deploy the complete frontend/dist directory to a static host.")
    doc.add_number(2, "Configure unknown application routes such as /research/capex-transmission to fall back to index.html.")
    doc.add_number(3, "Preserve /data paths and JSON MIME types.")
    doc.add_number(4, "Do not deploy frontend/src or data/processed as runtime dependencies; the browser needs only compiled assets and published public data.")
    doc.add_number(5, "Run a smoke test against the production URL: load the CapEx lens, switch every view, change correlation controls and move every scenario slider.")
    doc.add_callout(
        "No platform is currently encoded",
        "The repository contains no Vercel, Netlify, container or Sites hosting configuration. This guide therefore documents a platform-neutral static deployment. Platform-specific cache headers, access controls and rollback must be configured by the selected host.",
        color="D97706",
        shade="FFF7E6",
    )

    doc.add_heading("14. Operational failure modes", 1)
    doc.table(
        ["Failure", "Expected behaviour", "Operator action"],
        [
            ["Official Nifty endpoint changes", "Extractor raises on HTTP or unexpected response type; no processed replacement.", "Inspect landed/request contract; update extractor without weakening required-market checks."],
            ["Corporate provider missing a line item", "Fallback labels are tried; absent values remain null and coverage may shrink.", "Compare against company annual reports; do not substitute unrelated metrics."],
            ["Budget table definition changes", "Frozen series remains last valid; manual refresh must reconcile the capital column.", "Add a new source vintage and regression assertion."],
            ["Schema validation fails", "No processed or public JSON is written; any newly landed raw evidence remains available.", "Correct metadata, units, statuses or transform output; never hand-edit public JSON."],
            ["JSON replacement fails", "The current file remains valid, but files published earlier in the loop are not rolled back.", "Inspect filesystem permissions, correct the failure and rerun the complete ETL."],
            ["Catalogue references wrong adapter", "Frontend validator and runtime guard fail.", "Update types, schema enum, validator map and MetricPanel dispatch together."],
            ["Browser cache serves older data", "Asset version normally changes with catalogue generation.", "Verify catalogue version and host cache headers; invalidate static cache if required."],
            ["Scenario result looks implausible", "No backend failure occurs because inputs are user assumptions.", "Review every assumption, especially multiplier, lag, financing and nominal growth; treat as a scenario."],
        ],
        widths=[2200, 3300, 3500],
        font_size=14,
    )

    doc.add_heading("15. Technical debt and recommended next work", 1)
    recommendations = [
        ("Automate reference-source acquisition", "Replace the manual Statement 3, MoRTH, Railways and IIP transcriptions with document extractors, dated raw landing and table-identity checks while retaining the same typed boundary."),
        ("Version the scenario model", "Move the implemented parameters, uncertainty ranges and formulas into a schema-valid model definition and a pure calculation module shared by tests and UI."),
        ("Test frontend interactions", "Add component tests for direction switching, series colour stability, unit separation and preset/custom model transitions."),
        ("Catalogue the summary", "Register analysis-summary as an explicit asset and load it through the static client instead of a direct fetch."),
        ("Code-split specialised views", "Lazy-load correlation, corporate, fiscal and scenario components to address the Vite bundle warning."),
        ("Add deployment configuration", "Choose a static host, encode SPA fallback/cache policy and add production smoke checks."),
        ("Improve provenance granularity", "Attach source-document snapshot/checksum references to manually transcribed metadata and, where useful, individual observations."),
        ("Extend statistical governance", "Pre-register any inferential extension; avoid choosing lags or exclusions after viewing coefficients."),
    ]
    doc.table(["Recommendation", "Implementation direction"], recommendations, widths=[3000, 6000])

    doc.add_heading("16. File-level implementation index", 1)
    doc.table(
        ["File", "Reason to inspect it"],
        [
            ["scripts/config/capex_analysis.py", "Frozen research entities, roles, lags and output paths."],
            ["scripts/build_capex_pipeline.py", "Sole full and targeted ETL entry point."],
            ["scripts/extractors/capex_sources.py", "Live acquisition and immutable raw replay."],
            ["scripts/extractors/delivery_reference.py", "Typed extraction and validation of tracked manual source observations."],
            ["sources/capex_delivery_reference.json", "Version-controlled source input for allocation, delivery and IIP."],
            ["scripts/models/capex_sources.py", "Typed extraction-to-builder boundary."],
            ["scripts/models/capex_metrics.py", "Typed calculation-to-final-builder boundary."],
            ["scripts/transforms/capex_metrics.py", "Government, private and fiscal metric construction without JSON shaping."],
            ["scripts/builders/capex_artifacts.py", "Explicit direct call graph for all thirteen final artifacts."],
            ["scripts/builders/fiscal_outputs.py", "Execution and fiscal final payload builders."],
            ["scripts/builders/market_outputs.py", "Sector-performance and correlation final payload builders."],
            ["scripts/builders/real_economy_outputs.py", "Allocation, delivery, production, private and corporate final payload builders."],
            ["scripts/builders/evaluation_outputs.py", "Quality, state, crowding-in and summary final payload builders."],
            ["scripts/transforms/capex_analysis.py", "Market, correlation, fiscal-summary and alignment logic."],
            ["scripts/transforms/capex_depth.py", "Project-quality parsing, state fixed effects and crowding-in gates."],
            ["scripts/transforms/corporate_fundamentals.py", "Company growth and group medians."],
            ["scripts/sync_focused_catalogue.py", "Full narrative order and presentation configuration."],
            ["schemas/dated_multi_series.schema.json", "Primary chart-data contract."],
            ["schemas/market_performance.schema.json", "Market-data contract."],
            ["schemas/capex_analysis_summary.schema.json", "Verdict contract."],
            ["frontend/src/components/CapexCorrelationView.tsx", "Lead/lag explorer and fitted-line UI."],
            ["frontend/src/components/CorporateFundamentalsView.tsx", "Corporate case-study UI."],
            ["frontend/src/components/FiscalBridgeView.tsx", "Fiscal quadrant UI."],
            ["frontend/src/components/InvestmentQualityView.tsx", "Sector delivery-quality explorer."],
            ["frontend/src/components/CrowdingInView.tsx", "Distributed-lag evidence ladder."],
            ["frontend/src/components/StateCapexEvaluationView.tsx", "State panel explorer."],
            ["frontend/src/components/CapexScenarioLab.tsx", "Interactive five-year model."],
            ["frontend/src/components/MetricPanel.tsx", "Specialised component dispatch."],
            ["frontend/src/data/runtimeGuards.ts", "Runtime schema and adapter checks."],
            ["frontend/scripts/validate-public-data.mjs", "Build-time catalogue and asset validation."],
            ["tests/test_capex_analysis.py", "Market, timing, summary and company regression tests."],
            ["tests/test_capex_delivery.py", "Unit separation, exact source observations and output registration."],
            ["tests/test_capex_depth.py", "Quality/state/crowding-in contracts, evidence gates and public routes."],
            ["tests/test_capex_pipeline.py", "Layer boundaries, complete-set prevalidation, publication and processed/public parity."],
        ],
        widths=[3900, 5100],
        font_size=14,
    )
    doc.add_paragraph(
        "End of technical guide.",
        align="center",
        space_before=360,
        runs=[doc.run("End of technical guide.", italic=True, color="64748B")],
    )
    doc.save(TECHNICAL_GUIDE)


def validate_docx(path: Path) -> dict[str, int]:
    required = {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/styles.xml",
        "word/_rels/document.xml.rels",
    }
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = required - names
        if missing:
            raise ValueError(f"{path.name} missing DOCX parts: {sorted(missing)}")
        bad = archive.testzip()
        if bad:
            raise ValueError(f"{path.name} corrupt member: {bad}")
        xml = archive.read("word/document.xml").decode("utf-8")
    if "<w:tbl>" not in xml or "<w:pStyle w:val=\"Heading1\"/>" not in xml:
        raise ValueError(f"{path.name} lacks expected document structure")
    return {
        "bytes": path.stat().st_size,
        "paragraphs": xml.count("<w:p>"),
        "tables": xml.count("<w:tbl>"),
        "headings": xml.count("<w:pStyle w:val=\"Heading"),
        "hyperlinks": xml.count("<w:hyperlink"),
    }


def main() -> None:
    build_economic_guide()
    build_technical_guide()
    for path in (ECONOMIC_GUIDE, TECHNICAL_GUIDE):
        metrics = validate_docx(path)
        print(
            f"{path}: {metrics['bytes']} bytes, {metrics['paragraphs']} paragraphs, "
            f"{metrics['tables']} tables, {metrics['headings']} headings"
        )


if __name__ == "__main__":
    main()
