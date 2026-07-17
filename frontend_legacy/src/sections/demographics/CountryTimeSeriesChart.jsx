import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { getCountryKeys, mergeCountrySeries, countryLabel } from "../../lib/demographics";

const PEER_COLORS = ["#4FB8A8", "#7FA6D9", "#D9635A", "#B08AD9", "#62e45b"];

export default function CountryTimeSeriesChart({ data, loading, error, visibleCountries }) {
  if (loading) return <Panel title="Loading…"><LoadingBlock label="Loading indicator" /></Panel>;
  if (error) return <Panel title="Error"><ErrorBlock message={error} /></Panel>;
  if (!data) return null;

  const allKeys = getCountryKeys(data);
  const keys = visibleCountries ? allKeys.filter((k) => visibleCountries.includes(k)) : allKeys;
  const merged = mergeCountrySeries(data);
  const indiaKey = allKeys.find((k) => k.toLowerCase() === "india");

  return (
    <Panel
      title={data.metadata.label}
      subtitle={`${data.metadata.indicator_code} · ${data.metadata.start_year}–${data.metadata.end_year} · ${data.metadata.source}`}
    >
      <div className="h-80 -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={merged} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#223049" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="year"
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
              formatter={(value, name) => [value?.toFixed ? value.toFixed(1) : value, countryLabel(name)]}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, fontFamily: "IBM Plex Sans" }}
              formatter={(value) => countryLabel(value)}
            />
            {keys.map((key, i) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                name={key}
                stroke={key === indiaKey ? "#D9A441" : PEER_COLORS[i % PEER_COLORS.length]}
                strokeWidth={key === indiaKey ? 2.5 : 1.5}
                dot={false}
                connectNulls={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}
