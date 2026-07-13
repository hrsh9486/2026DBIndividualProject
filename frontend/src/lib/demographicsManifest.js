// One entry per indicator JSON file in public/data/demographics/.
// The file itself carries its own display label (metadata.label) and
// indicator_code, so this manifest only needs to say which files exist.
export const DEMOGRAPHIC_INDICATORS = [
  { file: "dependency_ratio" },
  { file: "electricity_access" },
  { file: "labor_force_participation" },
  { file: "literacy_rate" },
  { file: "urban_population" },
];
