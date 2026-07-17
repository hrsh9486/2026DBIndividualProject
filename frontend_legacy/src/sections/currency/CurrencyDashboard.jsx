import RebasedPerformanceChart from "./RebasedPerformanceChart";
import VolatilityTable from "./VolatilityTable";
import CorrelationHeatmap from "./CorrelationHeatmap";
import EventWindows from "./EventWindows";
import CrossDecomposition from "./CrossDecomposition";
import RealEffectiveExchangeRate from "./RealEffectiveExchangeRate";

export default function CurrencyDashboard() {
  return (
    <div className="space-y-4">
      <RealEffectiveExchangeRate />
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 space-y-4">
          <RebasedPerformanceChart />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <VolatilityTable />
            <CorrelationHeatmap />
          </div>
        </div>
        <div className="space-y-4">
          <CrossDecomposition />
          <EventWindows />
        </div>
      </div>
    </div>
  );
}
