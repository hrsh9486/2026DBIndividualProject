# React static-JSON frontend integration plan

## 1. Final architecture

There is no application API and no Node/Express server.

Node is used only for:

- installing and building the React application;
- running validation scripts;
- generating the frontend manifest if desired;
- testing the static data contracts.

At runtime, the browser fetches JSON files directly from React's `public` directory.

```text
Source-specific Python pipelines
        |
        | validate against one of the 3 existing JSON Schemas
        | write JSON artifacts
        v
public/
  data/
    catalogue.json
    schemas/
      annual_country_series.schema.json
      dated_multi_series.schema.json
      market_performance.schema.json
    equities/
    currency/
    macro/
    workforce/
    education/
    trade/
    formalisation/
        |
        | React build copies public files unchanged
        v
Browser
  fetch('/data/catalogue.json')
  fetch('/data/macro/cpi-inflation.json')
        |
        v
Schema-specific adapter -> chart rows -> React chart
```

The data files remain raw schema-valid documents. They are not wrapped in an API envelope.

## 2. Public-directory structure

```text
public/
  data/
    catalogue.json
    schemas/
      annual_country_series.schema.json
      dated_multi_series.schema.json
      market_performance.schema.json

    equities/
      market-performance.json
      rolling-correlations.json
      nifty-valuations.json
      institutional-flows.json

    currency/
      reer-world-bank.json
      reer-rbi.json
      fx-reserves.json

    macro/
      gdp-india.json
      gdp-peers.json
      twin-deficits.json
      government-capex.json
      cpi-inflation.json
      credit-growth.json
      central-government-debt.json

    workforce/
      lfpr.json
      lfpr-gender-ratio.json
      working-age-share.json
      youth-unemployment.json
      non-agricultural-employment.json

    education/
      tertiary-ger-world-bank.json
      tertiary-ger-aishe.json
      graduate-unemployment.json

    trade/
      services-export-share.json
      technology-exports.json
      fdi-inflows.json

    formalisation/
      upi-formalisation.json
```

The Python pipelines should write directly to these folders, or write to a staging directory that is copied into `public/data` after validation.

## 3. Static catalogue

Serve the frontend manifest as:

```text
/public/data/catalogue.json
```

which is fetched in the browser as:

```ts
fetch("/data/catalogue.json")
```

Each catalogue asset contains:

- `data_path`: the public browser path to the JSON file;
- `schema`: one of the three existing schema identifiers;
- `schema_path`: optional public path to the schema;
- expected frequency;
- staleness threshold;
- presentation configuration;
- asset availability.

Example:

```json
{
  "cpi-inflation": {
    "data_path": "/data/macro/cpi-inflation.json",
    "schema_path": "/data/schemas/dated_multi_series.schema.json",
    "schema": "dated_multi_series",
    "expected_frequency": "monthly",
    "stale_after_days": 60,
    "cache_strategy": "revalidate",
    "version": "2026-07-17"
  }
}
```

## 4. React loading flow

1. Load `/data/catalogue.json` once.
2. Resolve the selected section, indicator and view.
3. Read the view's `asset_id`.
4. Resolve the asset's `data_path` and declared schema.
5. Fetch the static JSON file.
6. Runtime-check the payload discriminator:
   - `metadata.country` plus `india` and `peers`;
   - `metadata.series_order` plus `series`;
   - `markets` plus market summaries.
7. Pass it to the matching adapter.
8. Render chart, summary cards, methodology and source information.

Use TanStack Query with the public path as the query key:

```ts
useQuery({
  queryKey: ["static-data", asset.data_path, asset.version],
  queryFn: () => loadStaticJson(asset.data_path),
  staleTime: 5 * 60 * 1000,
})
```

## 5. React directory structure

```text
src/
  data/
    staticDataClient.ts
    catalogue.ts
    runtimeGuards.ts

  adapters/
    annualCountryToRows.ts
    datedSeriesToRows.ts
    marketPerformanceToRows.ts

  components/
    dashboard/
      SectionGrid.tsx
      IndicatorCard.tsx

    charts/
      ChartShell.tsx
      CountryComparisonLine.tsx
      MultiSeriesLine.tsx
      MarketPerformanceChart.tsx
      ChartLegend.tsx
      DateRangeControl.tsx

    details/
      SummaryCards.tsx
      DataStatusBadge.tsx
      SourcePanel.tsx
      MethodologyPanel.tsx

  hooks/
    useCatalogue.ts
    useIndicatorData.ts

  pages/
    DashboardPage.tsx
    IndicatorPage.tsx
```

Recommended route:

```text
/indicators/:indicatorId?view=:viewId
```

## 6. The three adapters

### Annual country series

Convert:

```text
metadata + india[] + peers{}
```

into:

```ts
[
  { period: "2020", IND: 51.2, CHN: 68.1 },
  { period: "2021", IND: 52.0, CHN: 68.0 }
]
```

### Dated multi-series

Outer-join all requested series by ISO date:

```ts
[
  { period: "2026-05-31", pe_ratio: 22.1, pe_10y_average: 21.0 },
  { period: "2026-06-30", pe_ratio: 22.4, pe_10y_average: 21.1 }
]
```

Do not fill missing macro observations in React. Preserve `null`.

### Market performance

Select a field such as `normalized_value` and outer-join markets by date:

```ts
[
  { period: "2026-06-27", NIFTY_50: 111.8, SP500: 108.4 },
  { period: "2026-06-30", NIFTY_50: 112.0, SP500: 108.9 }
]
```

Summary cards read directly from each market's `summary`.

## 7. Validation without an API

Validation moves to the pipeline and build stages.

### Pipeline validation

Each Python extractor or exporter must:

1. build the JSON object;
2. validate it against its declared data schema;
3. run cross-field integrity checks;
4. write it to a temporary file;
5. atomically replace the public file only after validation succeeds.

### Frontend build validation

Run a Node validation script before `vite build` or `react-scripts build`.

It must verify:

- the catalogue matches the manifest schema;
- every `asset_id` referenced by a view exists;
- every `data_path` maps to an actual file under `public`;
- every static data file matches its declared data schema;
- the chart adapter is compatible with the declared schema;
- no series has duplicate dates or years;
- metadata date ranges match actual observation coverage.

Suggested scripts:

```json
{
  "scripts": {
    "validate:data": "node scripts/validate-public-data.mjs",
    "build": "npm run validate:data && vite build",
    "test": "vitest run"
  }
}
```

## 8. Caching and updates

Files in `public` are copied with stable names, so browsers may cache them.

For a small project, use:

```ts
fetch(path, { cache: "no-cache" })
```

or append the asset version:

```ts
fetch(`${path}?v=${asset.version}`)
```

The preferred approach is to update `asset.version` whenever the pipeline publishes a new file. TanStack Query should include that version in its query key.

For stronger immutable caching later, emit hashed filenames such as:

```text
cpi-inflation.7f8e2c1a.json
```

and regenerate `catalogue.json` with the new path.

## 9. Missing and stale data

- `null` represents a missing observation and must render as a chart gap, never zero.
- A missing static file should display an unavailable state.
- Compare `metadata.generated_at` or the latest observation date against `stale_after_days`.
- Display a stale-data badge but retain the last valid observations.
- Never substitute another source automatically.
- Display `provisional`, `revised`, `estimate` and `budget` status in the tooltip.

## 10. Percentage conventions

The existing schemas use two percentage conventions:

- Annual and dated economic series: `7.5` means `7.5%`.
- Market-performance returns and volatility: `0.075` means `7.5%`.

The catalogue's formatting configuration must remain authoritative:

- percentage-point data: `style="percent", scale=1`;
- decimal market returns: `style="percent", scale=100`.

Do not infer the convention from names or labels.

## 11. Metric-to-schema verification

All 23 indicators still fit into the three existing data schemas. Removing the API changes only file delivery, not the data contracts.

The six integration rules remain:

1. Rolling correlations are a separate `dated_multi_series` file.
2. WBI annual REER and RBI monthly REER remain separate files/views.
3. India quarterly GDP and annual peer GDP remain separate files/views.
4. Twin-deficit series must share a frequency and sign convention.
5. CapEx Actual, Revised Estimate and Budget Estimate use separate series keys.
6. WBI and AISHE tertiary-enrolment observations remain separate files/views.

No new observation schema is required.

## 12. Implementation order

### Phase 1

- Create `public/data` and copy the three schema files.
- Add `catalogue.json`.
- Implement the static JSON loader and three adapters.
- Render one representative indicator for each schema.

### Phase 2

- Publish all 23 indicators.
- Add date, entity and series controls.
- Add methodology, status and source panels.

### Phase 3

- Add build-time validation.
- Add atomic pipeline publishing.
- Add asset versioning or hashed filenames.
- Add fixture-based adapter tests.
