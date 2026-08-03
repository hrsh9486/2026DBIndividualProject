import { useJson } from "../../lib/dataLoader";
import CountryTimeSeriesChart from "../demographics/CountryTimeSeriesChart";
import PeerComparisonTable from "../demographics/PeerComparisonTable";

export default function RealEffectiveExchangeRate() {
  const { data, loading, error } = useJson("currency", "real_effective_exchange_rate");

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div className="xl:col-span-2">
        <CountryTimeSeriesChart data={data} loading={loading} error={error} />
      </div>
      <PeerComparisonTable data={data} loading={loading} error={error} />
    </div>
  );
}
