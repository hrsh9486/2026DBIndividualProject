export const SERIES_COLORS = [
  "#d45132",
  "#176b87",
  "#65733a",
  "#7b5c9a",
  "#c18b2f",
  "#4d6670",
] as const;

export function seriesColor(index: number) {
  return SERIES_COLORS[index % SERIES_COLORS.length];
}
