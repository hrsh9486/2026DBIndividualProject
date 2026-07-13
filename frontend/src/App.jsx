import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import TickerStrip from "./components/layout/TickerStrip";
import CurrencyDashboard from "./sections/currency/CurrencyDashboard";
import EquityDashboard from "./sections/equity/EquityDashboard";
import PendingSection from "./sections/placeholder/PendingSection";
import { SECTIONS, getSection } from "./lib/sections";

// Registry of live dashboards, keyed by section id. Add a new entry here
// (and flip `status: "live"` in lib/sections.js) once a bucket's real
// component is ready — everything else falls through to PendingSection.
const LIVE_DASHBOARDS = {
  currency: CurrencyDashboard,
  equity: EquityDashboard,
};

function SectionRoute() {
  const { sectionId } = useParams();
  const section = getSection(sectionId);

  if (!section) return <Navigate to="/currency" replace />;

  const LiveDashboard = section.status === "live" ? LIVE_DASHBOARDS[section.id] : null;

  return (
    <div>
      <div className="mb-5">
        <div className="font-mono text-xs text-[var(--color-text-faint)] uppercase tracking-wide">
          {section.number}
        </div>
        <h1 className="text-xl font-semibold mt-0.5">{section.label}</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">{section.blurb}</p>
      </div>
      {LiveDashboard ? <LiveDashboard /> : <PendingSection section={section} />}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[var(--color-ink-950)]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TickerStrip />
          <main className="flex-1 overflow-y-auto px-6 py-6">
            <Routes>
              <Route path="/" element={<Navigate to="/currency" replace />} />
              <Route path="/:sectionId" element={<SectionRoute />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

// Keep SECTIONS imported so this file fails loudly if the config is ever removed.
void SECTIONS;
