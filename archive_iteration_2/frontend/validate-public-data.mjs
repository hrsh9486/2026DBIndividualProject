import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const root = resolve(import.meta.dirname, "..");
const cataloguePath = resolve(root, "public/data/catalogue.json");
const catalogue = JSON.parse(readFileSync(cataloguePath, "utf8"));
const failures = [];
const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
const catalogueSchema = JSON.parse(readFileSync(resolve(root, "public/data/schemas/catalogue.schema.json"), "utf8"));
if (!ajv.validate(catalogueSchema, catalogue)) {
  failures.push(`catalogue schema: ${ajv.errorsText(ajv.errors, { separator: "; " })}`);
}
const dataValidators = Object.fromEntries([
  ["annual_country_series", "annual_country_series.schema.json"],
  ["dated_multi_series", "dated_multi_series.schema.json"],
  ["evidence_report", "evidence_report.schema.json"],
  ["market_performance", "market_performance.schema.json"],
].map(([name, file]) => [name, ajv.compile(JSON.parse(readFileSync(resolve(root, `public/data/schemas/${file}`), "utf8")))]));
const capexSummaryValidator = ajv.compile(JSON.parse(readFileSync(
  resolve(root, "public/data/schemas/capex_analysis_summary.schema.json"),
  "utf8",
)));
const adapters = {
  "country-comparison-line": "annual_country_series",
  "multi-series-line": "dated_multi_series",
  "market-performance": "market_performance",
  "capex-correlation": "dated_multi_series",
  "corporate-fundamentals": "dated_multi_series",
  "fiscal-bridge": "dated_multi_series",
  "capex-scenario-lab": "dated_multi_series",
  "investment-quality": "dated_multi_series",
  "state-capex-evaluation": "dated_multi_series",
  "crowding-in": "dated_multi_series",
};

for (const section of catalogue.sections ?? []) {
  if (section.evidence_asset_id) {
    const evidenceAsset = catalogue.assets[section.evidence_asset_id];
    if (!evidenceAsset) failures.push(`${section.id}: missing evidence asset ${section.evidence_asset_id}`);
    else if (evidenceAsset.schema !== "evidence_report") failures.push(`${section.id}: evidence asset must use evidence_report`);
  }
  for (const indicator of section.indicators ?? []) {
    if (!indicator.views.some((view) => view.id === indicator.default_view)) failures.push(`${indicator.id}: default view does not exist`);
    for (const view of indicator.views) {
      const asset = catalogue.assets[view.asset_id];
      if (!asset) { failures.push(`${indicator.id}/${view.id}: missing asset ${view.asset_id}`); continue; }
      if (adapters[view.presentation.component] !== asset.schema) failures.push(`${indicator.id}/${view.id}: adapter/schema mismatch`);
    }
  }
}

for (const [assetId, asset] of Object.entries(catalogue.assets ?? {})) {
  if (asset.availability === "planned") continue;
  const path = resolve(root, `public${asset.data_path}`);
  if (!existsSync(path)) { failures.push(`${assetId}: missing ${asset.data_path}`); continue; }
  const payload = JSON.parse(readFileSync(path, "utf8"));
  const schemaValid = dataValidators[asset.schema]?.(payload);
  if (!schemaValid) failures.push(`${assetId}: ${ajv.errorsText(dataValidators[asset.schema]?.errors, { separator: "; " })}`);
  const detected = payload.india && payload.peers ? "annual_country_series" : payload.series ? "dated_multi_series" : payload.markets ? "market_performance" : payload.analyses ? "evidence_report" : "unknown";
  if (detected !== asset.schema) failures.push(`${assetId}: expected ${asset.schema}, detected ${detected}`);
  if (detected === "annual_country_series") {
    const series = [payload.india, ...Object.values(payload.peers)];
    for (const values of series) {
      const years = values.map((point) => point.year);
      if (new Set(years).size !== years.length) failures.push(`${assetId}: duplicate years`);
    }
    const indiaYears = payload.india.map((point) => point.year);
    if (indiaYears.at(0) !== payload.metadata.start_year || indiaYears.at(-1) !== payload.metadata.end_year) failures.push(`${assetId}: metadata year range mismatch`);
  }
  if (detected === "dated_multi_series") {
    for (const [key, series] of Object.entries(payload.series)) {
      const dates = series.values.map((point) => point.date);
      if (new Set(dates).size !== dates.length) failures.push(`${assetId}/${key}: duplicate dates`);
    }
  }
  if (detected === "market_performance") {
    for (const [key, market] of Object.entries(payload.markets)) {
      const dates = market.series.map((point) => point.date);
      if (new Set(dates).size !== dates.length) failures.push(`${assetId}/${key}: duplicate dates`);
    }
  }
}

let evidenceReportCount = 0;
const evidenceDirectory = resolve(root, "public/data/evidence");
if (existsSync(evidenceDirectory)) {
  for (const file of readdirSync(evidenceDirectory).filter((name) => name.endsWith(".json")).sort()) {
    evidenceReportCount += 1;
    const payload = JSON.parse(readFileSync(resolve(evidenceDirectory, file), "utf8"));
    if (!dataValidators.evidence_report(payload)) {
      failures.push(`evidence/${file}: ${ajv.errorsText(dataValidators.evidence_report.errors, { separator: "; " })}`);
    }
  }
}

const capexSummaryPath = resolve(root, "public/data/capex-analysis/analysis-summary.json");
if (existsSync(capexSummaryPath)) {
  const payload = JSON.parse(readFileSync(capexSummaryPath, "utf8"));
  if (!capexSummaryValidator(payload)) {
    failures.push(`capex-analysis/analysis-summary.json: ${ajv.errorsText(capexSummaryValidator.errors, { separator: "; " })}`);
  }
}

if (failures.length) {
  console.error(`Static data validation failed:\n- ${failures.join("\n- ")}`);
  process.exit(1);
}
console.log(`Validated ${Object.keys(catalogue.assets).length} static assets, ${evidenceReportCount} evidence reports and ${catalogue.sections.length} sections.`);
