import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { useJson } from "../../lib/dataLoader";

const LINE_COLORS = {
  USDINR: "#D9A441", // marigold - anchor pair
  GBPINR: "#4FB8A8",
  EURINR: "#7FA6D9",
  JPYINR: "#D9635A",
  CHFINR: "#B08AD9",
};

export default function RebasedPerformanceChart() {
  const { data, loading, error } = useJson("currency", "rebased_performance");

  return (
    <Panel
      title="Rebased FX Performance"
      subtitle={data ? `Base ${data.metadata.base_date} = ${data.metadata.base_value}` : undefined}
    >
      {loading && <LoadingBlock label="Loading FX series" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <div className="h-80 -ml-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.series} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#223049" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: "#8592AB", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                axisLine={{ stroke: "#223049" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#8592AB", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                axisLine={{ stroke: "#223049" }}
                tickLine={false}
                domain={["auto", "auto"]}
              />
              <Tooltip
                contentStyle={{
                  background: "#17203A",
                  border: "1px solid #223049",
                  borderRadius: 6,
                  fontFamily: "IBM Plex Mono",
                  fontSize: 12,
                }}
                labelStyle={{ color: "#E8ECF4" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "IBM Plex Sans" }} />
              {data.metadata.pairs.map((pair) => (
                <Line
                  key={pair}
                  type="monotone"
                  dataKey={pair}
                  stroke={LINE_COLORS[pair] ?? "#8592AB"}
                  strokeWidth={pair === "USDINR" ? 2.5 : 1.5}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
