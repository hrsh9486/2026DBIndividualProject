// One entry per indicator JSON file in public/data/demographics/.
// The file itself carries its own display label (metadata.label) and
// indicator_code, so this manifest only needs to say which files exist.
export const DEMOGRAPHIC_INDICATORS = [
  // { file: "dependency_ratio" },
  { file: "electricity_access" },
  { file: "labor_force_participation" },
  { file: "literacy_rate" },
  { file: "female_to_male_lfpr_ratio" },
  { file: "pct_gdb_secondary_expenditure" },
  { file: "school_enrollment_gross_secondary" },
  { file: "school_enrollment_gross_tertiary" },
  { file: "urban_population" },
  { file: "working_age_share_pct" },
  { file: "youth_unemployment_rate" },
];
