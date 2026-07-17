import { useJson } from "../../lib/dataLoader";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import EquityHighlights from "./EquityHighlights";
import EquitySummaryTable from "./EquitySummaryTable";
import EquityRankings from "./EquityRankings";

export default function EquityDashboard() {
  const { data, loading, error } = useJson("etf", "etf_base_stats");

  if (loading) return <LoadingBlock label="Loading index & ETF stats" />;
  if (error) return <ErrorBlock message={error} />;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <EquityHighlights data={data} />
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <EquitySummaryTable data={data} />
        </div>
        <EquityRankings data={data} />
      </div>
    </div>
  );
}
