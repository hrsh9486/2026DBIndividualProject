import { Outlet } from "react-router-dom";
import { useCatalogue } from "../hooks/useCatalogue";
import Sidebar from "./Sidebar";

export default function Layout() {
  const { data } = useCatalogue();
  return <div className="app-shell">
    <Sidebar />
    <div className="site-frame">
      <header className="topbar"><span>India public CapEx transmission</span><div className="topbar-meta"><span className="live-dot" />{Object.keys(data?.assets ?? {}).length} published datasets</div></header>
      <main><Outlet /></main>
      <footer><span>CapEx research</span><span>Static, schema-validated data</span><span>Schema v{data?.schema_version ?? "—"}</span></footer>
    </div>
  </div>;
}
