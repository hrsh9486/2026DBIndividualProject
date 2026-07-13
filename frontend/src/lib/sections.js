// Single source of truth for the 7 analytical buckets.
// `status: "live"` sections have real components + data wired up.
// `status: "pending"` sections render the placeholder shell so nav/routing
// is ready before the underlying scripts + JSON exist.

export const SECTIONS = [
  {
    id: "equity",
    number: "01",
    label: "Equity Markets",
    blurb: "Nifty 50, Sensex, sector indices, global benchmark comparisons",
    status: "live",
  },
  {
    id: "currency",
    number: "02",
    label: "Currency",
    blurb: "INR multi-currency performance, volatility, and stress episodes",
    status: "live",
  },
  {
    id: "macro",
    number: "03",
    label: "Macro & Monetary",
    blurb: "CPI/WPI, repo rate, current account, oil dependency, NPAs, credit growth",
    status: "pending",
  },
  {
    id: "demographics",
    number: "04",
    label: "Demographics & Human Capital",
    blurb: "Working-age population, dependency ratio, LFPR, literacy",
    status: "live",
  },
  {
    id: "gov-spending",
    number: "05",
    label: "Government Spending",
    blurb: "Defence, manufacturing, space, health, exports, capex, subsidies",
    status: "pending",
  },
  {
    id: "structural",
    number: "06",
    label: "Structural / Sectoral",
    blurb: "Agriculture GDP-vs-employment mismatch, UPI & digital infrastructure",
    status: "pending",
  },
  {
    id: "external",
    number: "07",
    label: "External / Global Context",
    blurb: "Fed policy, DXY, oil prices, China+1, ASEAN comparisons, FII/FPI flows",
    status: "pending",
  },
];

export const getSection = (id) => SECTIONS.find((s) => s.id === id);
