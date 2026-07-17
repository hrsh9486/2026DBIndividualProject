import { readFileSync, existsSync } from "node:fs";
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
  ["market_performance", "market_performance.schema.json"],
].map(([name, file]) => [name, ajv.compile(JSON.parse(readFileSync(resolve(root, `public/data/schemas/${file}`), "utf8")))]));
const adapters = {
  "country-comparison-line": "annual_country_series",
  "multi-series-line": "dated_multi_series",
  "market-performance": "market_performance",
};

for (const section of catalogue.sections ?? []) {
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
  const detected = payload.india && payload.peers ? "annual_country_series" : payload.series ? "dated_multi_series" : payload.markets ? "market_performance" : "unknown";
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

if (failures.length) {
  console.error(`Static data validation failed:\n- ${failures.join("\n- ")}`);
  process.exit(1);
}
console.log(`Validated ${Object.keys(catalogue.assets).length} static assets and ${catalogue.sections.length} sections.`);
