import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useCatalogue } from "../hooks/useCatalogue";
import Sidebar from "./Sidebar";

export default function Layout() {
  const { data } = useCatalogue();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => setMenuOpen(false), [location.pathname, location.hash]);
  useEffect(() => {
    if (!menuOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && setMenuOpen(false);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen]);

  return <div className="app-shell">
    <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
    {menuOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
    <div className="site-frame">
      <header className="topbar">
        <button className="menu-toggle" type="button" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><i /><i /><i /></button>
        <span>India public CapEx transmission</span>
        <div className="topbar-meta"><span className="live-dot" />{Object.keys(data?.assets ?? {}).length} published datasets</div>
      </header>
      <main><Outlet /></main>
      <footer><span>CapEx research</span><span>Static, schema-validated data</span><span>Schema v{data?.schema_version ?? "—"}</span></footer>
    </div>
  </div>;
}
