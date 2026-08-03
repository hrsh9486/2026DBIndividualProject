# Metric-to-schema audit

**Result:** All 23 indicators can be represented by the three existing data schemas. Seventeen fit directly; six require an export or view rule rather than a new schema.

| # | Section | Indicator | Schema | Fit | Integration rule |
|---:|---|---|---|---|---|
| 1 | Equities | India vs. global equity-index performance | `market_performance` | **Conditional** | Core prices and scalar statistics fit. Export rolling correlation as a separate dated_multi_series asset; the market schema only stores point correlations. |
| 2 | Equities | Index P/E vs. 10-year rolling average | `dated_multi_series` | **Clean** | Use ratio lines on the left axis and premium/discount percentage on the right. |
| 3 | Equities | Implied index earnings growth (YoY) | `dated_multi_series` | **Clean** | Use implied_eps and implied_eps_yoy_pct in the same source artifact or a dedicated view. |
| 4 | Equities | DII vs. FII/FPI net equity flows | `dated_multi_series` | **Clean** | Flow lines share a currency unit; put the optional offset ratio on a secondary axis. |
| 5 | Currency | Real Effective Exchange Rate (REER) | `annual_country_series / dated_multi_series` | **Conditional** | Use annual_country_series for WBI peers and a separate dated_multi_series asset for RBI monthly data. Do not splice them. |
| 6 | Currency | Foreign-exchange reserves and import cover | `dated_multi_series` | **Clean** | Mixed units are supported per series; render with two axes. |
| 7 | Macro | Real, nominal and real per-capita GDP growth | `dated_multi_series / annual_country_series` | **Conditional** | Use one common frequency per asset. Keep India quarterly data separate from annual peer comparisons. |
| 8 | Macro | Fiscal deficit and current-account deficit (% GDP) | `dated_multi_series` | **Conditional** | Align both lines to the same frequency and sign convention before export. |
| 9 | Macro | Central government CapEx (% total expenditure) | `dated_multi_series` | **Conditional** | Represent Actual, Revised Estimate and Budget Estimate as separate series keys. Avoid duplicate dates in one series. |
| 10 | Macro | Headline vs. core CPI inflation | `dated_multi_series` | **Clean** | Both monthly percentage-point series share one axis. |
| 11 | Macro | Non-food credit growth vs. nominal GDP growth | `dated_multi_series` | **Clean** | Align both inputs to quarterly frequency; include the growth gap as a third line. |
| 12 | Macro | Central government debt (% GDP) | `annual_country_series` | **Clean** | One annual country-comparison series. |
| 13 | Workforce | Labour Force Participation Rate (LFPR) | `annual_country_series` | **Clean** | One annual country-comparison series. |
| 14 | Workforce | Female-to-male LFPR ratio | `annual_country_series` | **Clean** | Derived annual ratio; set is_derived=true and document whether values are ratios or percentages. |
| 15 | Workforce | Working-age population share | `annual_country_series` | **Clean** | One annual country-comparison series. |
| 16 | Workforce | Youth unemployment rate | `annual_country_series` | **Clean** | One annual country-comparison series. |
| 17 | Workforce | Non-agricultural employment share | `annual_country_series` | **Clean** | Derived annual percentage; set is_derived=true. |
| 18 | Education | Tertiary Gross Enrolment Ratio | `annual_country_series` | **Conditional** | Keep WBI peer data and AISHE India detail as separate assets/views rather than one spliced time series. |
| 19 | Education | Graduate-and-above unemployment rate | `annual_country_series` | **Clean** | India-only use is valid with metadata.peers=[] and peers={}. |
| 20 | Trade | Services share of services-plus-merchandise exports | `annual_country_series` | **Clean** | Derived annual percentage; set is_derived=true. |
| 21 | Trade | Medium- and high-technology exports (% manufactured exports) | `annual_country_series` | **Clean** | One annual country-comparison series. |
| 22 | Trade | FDI net inflows (% GDP) | `annual_country_series` | **Clean** | One annual country-comparison series; negative values remain valid. |
| 23 | Formalisation | UPI transaction volume per capita and value (% GDP) | `dated_multi_series` | **Clean** | Mixed units are supported per series; document the GDP denominator used for monthly normalisation. |