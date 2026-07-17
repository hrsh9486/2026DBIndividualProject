import { useQuery } from "@tanstack/react-query";
import { loadStaticAsset } from "../data/staticDataClient";
import type { StaticDataAsset } from "../data/types";

export const useIndicatorData = (asset?: StaticDataAsset) => useQuery({
  queryKey: ["static-data", asset?.data_path, asset?.version],
  queryFn: () => loadStaticAsset(asset!),
  enabled: Boolean(asset && asset.availability !== "planned"),
});
