import type {
  EvidenceAnalysis,
  EvidenceDiagnostic,
  EvidenceEstimate,
  EvidenceStatus,
  StaticDataAsset,
} from "../data/types";
import { useEvidenceData } from "../hooks/useEvidenceData";
import DataStatusBadge from "./DataStatusBadge";
import { ErrorPanel, LoadingPanel } from "./StatePanel";

const STATUS_LABELS: Record<EvidenceStatus, string> = {
  supported: "Supported under registered design",
  not_supported: "Registered claim not supported",
  mixed: "Mixed evidence",
  descriptive_only: "Descriptive only",
  insufficient_data: "Insufficient data",
  failed_diagnostics: "Registered diagnostic failure",
};

const humanise = (value: string) => value.replaceAll("_", " ");

function formatNumber(value: number | null, decimals = 3): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-IN", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  });
}

function formatPValue(value: number | null): string {
  if (value === null) return "—";
  if (value < 0.0001) return value.toExponential(2);
  return value.toFixed(4);
}

function formatEstimateValue(estimate: EvidenceEstimate): string {
  const value = formatNumber(estimate.value);
  if (estimate.unit === "percent_per_year") return `${value}% per year`;
  if (estimate.unit === "transactions_per_person_per_year") {
    return `${value} transactions per person per year`;
  }
  if (estimate.unit.includes("_per_")) return `${value} pp per 1 pp`;
  if (estimate.unit === "percent") return `${value}%`;
  return `${value} ${humanise(estimate.unit)}`;
}

function intervalText(estimate: EvidenceEstimate): string {
  if (!estimate.confidence_interval) return "Not reported";
  const [low, high] = estimate.confidence_interval;
  const suffix = estimate.unit === "percent_per_year"
    ? "% per year"
    : estimate.unit === "transactions_per_person_per_year"
    ? "transactions per person per year"
    : estimate.unit.includes("_per_")
    ? "pp per 1 pp"
    : estimate.unit === "percent"
    ? "%"
    : humanise(estimate.unit);
  return `${formatNumber(low)} to ${formatNumber(high)}${suffix ? ` ${suffix}` : ""}`;
}

function diagnosticValue(diagnostic: EvidenceDiagnostic): string {
  if (diagnostic.value === null) return "Not available";
  if (typeof diagnostic.value === "boolean") return diagnostic.value ? "Yes" : "No";
  if (typeof diagnostic.value === "number") return formatNumber(diagnostic.value, 4);
  return diagnostic.value;
}

function AnalysisSummary({ analysis }: { analysis: EvidenceAnalysis }) {
  const focal = analysis.estimates.filter((estimate) => estimate.is_focal);
  const failedDiagnostics = analysis.diagnostics.filter(
    (diagnostic) => diagnostic.passed === false,
  );
  const robustnessSupported = analysis.robustness.filter(
    (result) => result.status === "supported",
  ).length;

  return <article className="evidence-analysis">
    <header className="evidence-analysis-header">
      <div>
        <span>Specification {analysis.specification_version} · {humanise(analysis.evidence_class)}</span>
        <h3>{analysis.label}</h3>
      </div>
      <div className="evidence-labels">
        <span className={`evidence-status status-${analysis.status}`}>
          {STATUS_LABELS[analysis.status]}
        </span>
        <span className="evidence-grade">Grade: {humanise(analysis.grade)}</span>
      </div>
    </header>

    <div className="evidence-claim">
      <span>Registered claim</span>
      <p>{analysis.claim}</p>
    </div>

    <p className="evidence-interpretation">{analysis.practical_interpretation}</p>

    {failedDiagnostics.length > 0 && <div className="evidence-warning" role="note">
      <strong>Why this result is constrained</strong>
      <p>{failedDiagnostics.map((item) => humanise(item.key)).join(", ")} failed the predeclared diagnostic threshold. Statistical significance or robustness checks do not override that failure.</p>
    </div>}

    <div className="evidence-summary-grid">
      <section>
        <span>Focal estimate</span>
        {focal.length ? focal.map((estimate) => <div key={estimate.term}>
          <strong>{formatEstimateValue(estimate)}</strong>
          <p>95% interval: {intervalText(estimate)}</p>
          <p>Adjusted p-value: {formatPValue(estimate.adjusted_p_value)}</p>
        </div>) : <strong>No inferential estimate</strong>}
      </section>
      <section>
        <span>Analysis sample</span>
        <strong>{analysis.sample.n} observations</strong>
        <p>{analysis.sample.start_date ?? "—"} to {analysis.sample.end_date ?? "—"}</p>
        <p>{humanise(analysis.sample.frequency)}</p>
      </section>
      <section>
        <span>Robustness</span>
        <strong>{robustnessSupported} of {analysis.robustness.length} supported</strong>
        <p>Registered expected direction: {humanise(analysis.expected_direction)}</p>
        <p>{humanise(analysis.support_rule)}</p>
      </section>
    </div>

    <details className="evidence-details">
      <summary>Inspect estimates, diagnostics, robustness and method</summary>
      <div className="evidence-detail-grid">
        <section>
          <h4>All reported estimates</h4>
          <div className="evidence-table-wrap">
            <table>
              <thead><tr><th>Term</th><th>Estimate</th><th>95% interval</th><th>p</th><th>Adjusted p</th></tr></thead>
              <tbody>{analysis.estimates.map((estimate) => <tr key={estimate.term}>
                <th scope="row">{humanise(estimate.term)}{estimate.is_focal ? " · focal" : ""}</th>
                <td>{formatEstimateValue(estimate)}</td>
                <td>{intervalText(estimate)}</td>
                <td>{formatPValue(estimate.p_value)}</td>
                <td>{formatPValue(estimate.adjusted_p_value)}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </section>

        <section>
          <h4>Registered diagnostics</h4>
          <div className="diagnostic-list">{analysis.diagnostics.map((diagnostic) => <div key={diagnostic.key}>
            <div>
              <strong>{humanise(diagnostic.key)}</strong>
              <span className={diagnostic.passed === false ? "diagnostic-fail" : diagnostic.passed === true ? "diagnostic-pass" : ""}>
                {diagnostic.passed === true ? "Pass" : diagnostic.passed === false ? "Fail" : "Not assessed"}
              </span>
            </div>
            <p>Value: {diagnosticValue(diagnostic)}{diagnostic.threshold === null ? "" : ` · threshold ${formatNumber(diagnostic.threshold, 4)}`}</p>
            <small>{diagnostic.interpretation}</small>
          </div>)}</div>
        </section>

        <section>
          <h4>Registered robustness</h4>
          <div className="robustness-list">{analysis.robustness.map((result) => <div key={result.specification}>
            <div>
              <strong>{humanise(result.specification)}</strong>
              <span>{STATUS_LABELS[result.status]}</span>
            </div>
            <p>{result.sample_size} observations{result.focal_estimate ? ` · estimate ${formatEstimateValue(result.focal_estimate)} · p=${formatPValue(result.focal_estimate.p_value)}` : ""}</p>
            <small>{result.note}</small>
          </div>)}</div>
        </section>

        <section className="evidence-method">
          <h4>Method and boundaries</h4>
          <dl>
            <div><dt>Null hypothesis</dt><dd>{analysis.null_hypothesis ?? "Not applicable"}</dd></div>
            <div><dt>Formula</dt><dd><code>{analysis.method.formula}</code></dd></div>
            <div><dt>Uncertainty</dt><dd>{analysis.method.covariance ?? "None"}{analysis.method.max_lags === null ? "" : `, maximum lag ${analysis.method.max_lags}`}</dd></div>
            <div><dt>Alignment</dt><dd>{humanise(analysis.method.alignment)}</dd></div>
            <div><dt>Causal claim</dt><dd>{analysis.causal ? "Yes" : "No — observational association only"}</dd></div>
          </dl>
          <p className="evidence-limitation">{analysis.limitation}</p>
        </section>
      </div>
    </details>
  </article>;
}

export default function EvidencePanel({ asset }: { asset: StaticDataAsset }) {
  const query = useEvidenceData(asset);
  if (asset.schema !== "evidence_report") {
    return <ErrorPanel message="The lens evidence asset has the wrong contract" />;
  }
  return <section id="evidence" className="evidence-panel" aria-labelledby="evidence-title">
    <header className="evidence-panel-header">
      <div>
        <span>Registered statistical evidence</span>
        <h2 id="evidence-title">Evidence assessment</h2>
        <p>Predeclared observational models are shown separately from the descriptive metrics below. A low p-value does not override a failed diagnostic or the registered expected direction.</p>
      </div>
      {query.data && <DataStatusBadge
        generatedAt={query.data.metadata.generated_at}
        staleAfterDays={asset.stale_after_days}
      />}
    </header>
    {query.isLoading && <LoadingPanel />}
    {query.error && <ErrorPanel message={query.error.message} />}
    {query.data && <>
      <div className="evidence-analysis-list">
        {query.data.analyses.map((analysis) =>
          <AnalysisSummary key={analysis.analysis_key} analysis={analysis} />
        )}
      </div>
      <footer className="evidence-provenance">
        <div><span>Registry</span><strong>{query.data.metadata.specification_registry_version}</strong></div>
        <div><span>Multiple testing</span><strong>{humanise(query.data.metadata.multiple_testing.method)} · α {query.data.metadata.multiple_testing.alpha}</strong></div>
        <div><span>Source artifacts</span><strong>{query.data.metadata.source_assets.map((source) => source.path).join(", ")}</strong></div>
      </footer>
    </>}
  </section>;
}
