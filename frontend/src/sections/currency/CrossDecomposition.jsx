import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { useJson } from "../../lib/dataLoader";

export default function CrossDecomposition() {
  const { data, loading, error } = useJson("currency", "cross_decomposition");

  return (
    <Panel title="Cross-Pair Decomposition" subtitle="INR leg vs. counter-currency leg contribution">
      {loading && <LoadingBlock label="Loading decomposition" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.pairs} layout="vertical" margin={{ left: 8, right: 12 }}>
              <CartesianGrid stroke="#223049" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: "#8592AB", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                axisLine={{ stroke: "#223049" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="pair"
                tick={{ fill: "#E8ECF4", fontSize: 12, fontFamily: "IBM Plex Mono" }}
                axisLine={{ stroke: "#223049" }}
                tickLine={false}
                width={70}
              />
              <Tooltip
                contentStyle={{
                  background: "#17203A",
                  border: "1px solid #223049",
                  borderRadius: 6,
                  fontFamily: "IBM Plex Mono",
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "IBM Plex Sans" }} />
              <Bar dataKey="inr_contribution_pct" name="INR leg" stackId="a" fill="#D9A441" radius={[3, 0, 0, 3]} />
              <Bar dataKey="gbp_contribution_pct" name="Counter-currency leg" stackId="a" fill="#4FB8A8" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
