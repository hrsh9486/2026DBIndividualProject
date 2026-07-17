import { Outlet } from "react-router-dom";
import { useCatalogue } from "../hooks/useCatalogue";
import Sidebar from "./Sidebar";

export default function Layout() {
  const { data } = useCatalogue();
  return <div className="app-shell">
    <Sidebar />
    <div className="site-frame">
      <header className="topbar"><span>India economic indicators</span><div className="topbar-meta"><span className="live-dot" />{Object.keys(data?.assets ?? {}).length} published datasets</div></header>
      <main><Outlet /></main>
      <footer><span>Public economic data</span><span>No application API</span><span>Schema v{data?.schema_version ?? "—"}</span></footer>
    </div>
  </div>;
}
