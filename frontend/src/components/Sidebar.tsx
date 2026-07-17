import { NavLink, useLocation } from "react-router-dom";
import { useCatalogue } from "../hooks/useCatalogue";

export default function Sidebar() {
  const { data } = useCatalogue();
  const location = useLocation();
  return <aside className="sidebar">
    <NavLink to="/" className="sidebar-brand"><span>ID</span><strong>India<br />Data</strong></NavLink>
    <nav className="sidebar-nav" aria-label="Research metrics">
      <NavLink to="/" end className="sidebar-home">Overview</NavLink>
      {[...(data?.sections ?? [])].sort((a, b) => a.order - b.order).map((section) => {
        const active = location.pathname === `/research/${section.id}`;
        return <div className="sidebar-group" key={section.id}>
          <NavLink to={`/research/${section.id}`} className={active ? "lens-link active" : "lens-link"}>
            <span>{String(section.order).padStart(2, "0")}</span>{section.label}
          </NavLink>
          <div className="metric-links">{section.indicators.map((indicator) =>
            <a key={indicator.id} href={`/research/${section.id}#${indicator.id}`}>{indicator.title}</a>
          )}</div>
        </div>;
      })}
    </nav>
    <div className="sidebar-foot"><i />Static data verified at build</div>
  </aside>;
}
