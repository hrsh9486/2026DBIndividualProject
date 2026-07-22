import { Link } from "react-router-dom";
import { useCatalogue } from "../hooks/useCatalogue";
import { ErrorPanel, LoadingPanel } from "../components/StatePanel";

export default function DashboardPage() {
  const { data, isLoading, error } = useCatalogue();
  if (isLoading) return <LoadingPanel />;
  if (error || !data) return <ErrorPanel message={error?.message ?? "Catalogue unavailable"} />;
  const activeCount = Object.values(data.assets).filter((asset) => asset.availability !== "planned").length;
  const availableIndicators = data.sections.flatMap((section) => section.indicators).filter((indicator) => {
    const view = indicator.views.find((candidate) => candidate.id === indicator.default_view) ?? indicator.views[0];
    return data.assets[view.asset_id]?.availability !== "planned";
  }).length;
  const newest = Object.values(data.assets).map((asset) => asset.version).filter(Boolean).sort().at(-1);

  return <div className="landing-page">
    <section className="hero compact">
      <div className="eyebrow">India and peer economies</div>
      <h1>Economic indicators</h1>
      <p>Browse published market, currency, macroeconomic, workforce, education and trade data.</p>
      <div className="hero-stats">
        <div><strong>{activeCount}</strong><span>Live datasets</span></div>
        <div><strong>{data.sections.length}</strong><span>Research lenses</span></div>
        <div><strong>{newest ?? "—"}</strong><span>Latest build</span></div>
      </div>
    </section>

    <section className="coverage-strip">
      <span>Coverage</span>
      <div><b>{availableIndicators}</b> available metric views</div>
      <div><b>{data.roadmap_total ?? 23}</b> target indicators</div>
      <div className="coverage-bar"><i style={{ width: `${Math.min(100, availableIndicators / (data.roadmap_total ?? 23) * 100)}%` }} /></div>
    </section>

    <div className="section-list">
      {[...data.sections].sort((a, b) => a.order - b.order).map((section) => <section id={`section-${section.id}`} key={section.id} className="catalogue-section">
        <div className="section-heading"><span>{String(section.order).padStart(2, "0")}</span><div><h2>{section.label}</h2><p>{section.indicators.length} published indicator{section.indicators.length === 1 ? "" : "s"}</p></div></div>
        <div className="indicator-grid">{section.indicators.map((indicator) => {
          const view = indicator.views.find((candidate) => candidate.id === indicator.default_view) ?? indicator.views[0];
          const asset = data.assets[view.asset_id];
          return <Link key={indicator.id} to={`/research/${section.id}#${indicator.id}`} className="indicator-card">
            <div className="card-top"><span>{asset.availability ?? "active"}</span><i>{asset.expected_frequency}</i></div>
            <h3>{indicator.title}</h3><p>{indicator.summary}</p>
            <div className="card-foot"><span>View research lens</span><b>↗</b></div>
          </Link>;
        })}</div>
      </section>)}
    </div>
  </div>;
}
