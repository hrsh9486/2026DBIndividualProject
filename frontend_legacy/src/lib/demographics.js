// Display names for country codes that show up in demographics JSON.
// Keys are matched case-insensitively (the india series is lowercased "india",
// peers are ISO alpha-3 codes) so lookups should go through countryLabel().
export const COUNTRY_NAMES = {
  IND: "India",
  CHN: "China",
  VNM: "Vietnam",
  IDN: "Indonesia",
  BGD: "Bangladesh",
  THA: "Thailand",
  PHL: "Philippines",
  MEX: "Mexico",
  ZAF: "South Africa",
  BRA: "Brazil",
};

export function countryLabel(code) {
  const upper = code.toUpperCase();
  if (upper === "INDIA") return "India";
  return COUNTRY_NAMES[upper] ?? code;
}

// Every demographics JSON file has this shape:
//   { metadata: {...}, india: [{year, value}, ...], peers: { CHN: [...], VNM: [...], ... } }
// "india" is a top-level array; every peer country lives inside the nested
// `peers` object, keyed by ISO alpha-3 code.

export function getCountryKeys(data) {
  const peerKeys = Object.keys(data.peers ?? {});
  const orderedPeers = data.metadata?.peers?.filter((p) => peerKeys.includes(p)) ?? [];
  const remainingPeers = peerKeys.filter((k) => !orderedPeers.includes(k));
  return ["india", ...orderedPeers, ...remainingPeers];
}

// Returns the [{year, value}] array for a given key from getCountryKeys(),
// reading from the right place depending on whether it's india or a peer.
export function getCountrySeries(data, key) {
  if (key === "india") return data.india ?? [];
  return data.peers?.[key] ?? [];
}

// Merges india + every peer's [{year, value}] array into one array of
// {year, india: value, CHN: value, ...} rows, sorted by year, for Recharts.
export function mergeCountrySeries(data) {
  const countryKeys = getCountryKeys(data);
  const byYear = new Map();

  for (const key of countryKeys) {
    const series = getCountrySeries(data, key);
    if (!Array.isArray(series)) continue; // guard against unexpected shapes
    for (const point of series) {
      const row = byYear.get(point.year) ?? { year: point.year };
      row[key] = point.value;
      byYear.set(point.year, row);
    }
  }

  return [...byYear.values()].sort((a, b) => a.year - b.year);
}

// Latest non-null value for a country, and the year it's from.
export function latestValue(series) {
  for (let i = series.length - 1; i >= 0; i--) {
    if (series[i].value !== null && series[i].value !== undefined) {
      return { year: series[i].year, value: series[i].value };
    }
  }
  return null;
}

// Earliest non-null value for a country.
export function earliestValue(series) {
  for (const point of series) {
    if (point.value !== null && point.value !== undefined) {
      return { year: point.year, value: point.value };
    }
  }
  return null;
}
