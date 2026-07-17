import { useState, useMemo } from "react";
import { useJson } from "../../lib/dataLoader";
import { DEMOGRAPHIC_INDICATORS } from "../../lib/demographicsManifest";
import { getCountryKeys, countryLabel } from "../../lib/demographics";
import CountryTimeSeriesChart from "./CountryTimeSeriesChart";
import PeerComparisonTable from "./PeerComparisonTable";
import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";

// Labels shown in the indicator dropdown before the file has loaded once.
// After that, each file's own metadata.label takes over (see loadedLabels).
function fileFallbackLabel(file) {
  return file.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function DemographicsDashboard() {
  const [indicatorFile, setIndicatorFile] = useState(DEMOGRAPHIC_INDICATORS[0]?.file);
  const { data, loading, error } = useJson("demographics", indicatorFile);
  const [hiddenCountries, setHiddenCountries] = useState([]);

  const countryKeys = useMemo(() => (data ? getCountryKeys(data) : []), [data]);
  const visibleCountries = countryKeys.filter((k) => !hiddenCountries.includes(k));

  function toggleCountry(key) {
    setHiddenCountries((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  return (
    <div className="space-y-4">
      <Panel>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-mono uppercase tracking-wide text-[var(--color-text-faint)]">
            Indicator
          </label>
          <select
            value={indicatorFile}
            onChange={(e) => {
              setIndicatorFile(e.target.value);
              setHiddenCountries([]);
            }}
            className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-2 py-1.5 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-marigold)]"
          >
            {DEMOGRAPHIC_INDICATORS.map(({ file }) => (
              <option key={file} value={file}>
                {data && file === indicatorFile ? data.metadata.label : fileFallbackLabel(file)}
              </option>
            ))}
          </select>

          {countryKeys.length > 0 && (
            <div className="flex flex-wrap gap-2 ml-auto">
              {countryKeys.map((key) => {
                const isHidden = hiddenCountries.includes(key);
                return (
                  <button
                    key={key}
                    onClick={() => toggleCountry(key)}
                    className={[
                      "text-xs font-mono px-2 py-1 rounded-full border transition-colors",
                      isHidden
                        ? "border-[var(--color-border)] text-[var(--color-text-faint)]"
                        : "border-[var(--color-marigold-dim)] text-[var(--color-text-primary)] bg-[var(--color-panel-raised)]",
                    ].join(" ")}
                  >
                    {countryLabel(key)}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </Panel>

      {loading && <LoadingBlock label="Loading indicator" />}
      {error && <ErrorBlock message={error} />}

      {data && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <CountryTimeSeriesChart data={data} visibleCountries={visibleCountries} />
          </div>
          <PeerComparisonTable data={data} />
        </div>
      )}
    </div>
  );
}
