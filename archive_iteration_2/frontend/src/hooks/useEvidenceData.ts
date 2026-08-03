import { useQuery } from "@tanstack/react-query";
import { assertEvidenceReport } from "../data/runtimeGuards";
import { loadStaticAsset } from "../data/staticDataClient";
import type { StaticDataAsset } from "../data/types";

export const useEvidenceData = (asset?: StaticDataAsset) => useQuery({
  queryKey: ["evidence-report", asset?.data_path, asset?.version],
  queryFn: async () => {
    const payload = await loadStaticAsset(asset!);
    assertEvidenceReport(payload);
    return payload;
  },
  enabled: Boolean(
    asset
    && asset.schema === "evidence_report"
    && asset.availability !== "planned"
  ),
});
