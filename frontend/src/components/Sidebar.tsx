import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useCatalogue } from "../hooks/useCatalogue";
import type { Indicator } from "../data/types";

const STORY_PATH = "/research/capex-transmission";

const chapters = [
  {
    number: "01",
    label: "Inputs & delivery",
    ids: ["capex-policy-input", "capex-sector-delivery", "capex-investment-quality"],
  },
  {
    number: "02",
    label: "Transmission",
    ids: [
      "capex-market-transmission",
      "capex-lag-test",
      "capex-corporate-case-study",
      "capex-real-conversion",
      "capex-crowding-in-depth",
      "capex-state-evaluation",
    ],
  },
  {
    number: "03",
    label: "Fiscal constraint",
    ids: ["capex-fiscal-constraint"],
  },
  {
    number: "04",
    label: "Scenario lab",
    ids: ["capex-scenario-lab"],
  },
] as const;

const shortLabels: Record<string, string> = {
  "capex-policy-input": "CapEx intensity & execution",
  "capex-sector-delivery": "Sector allocation & delivery",
  "capex-investment-quality": "Investment quality",
  "capex-market-transmission": "Sector market response",
  "capex-lag-test": "Market timing",
  "capex-corporate-case-study": "Corporate fundamentals",
  "capex-real-conversion": "Private investment",
  "capex-crowding-in-depth": "Crowding-in evidence",
  "capex-state-evaluation": "State evaluation",
  "capex-fiscal-constraint": "Fiscal sustainability",
  "capex-scenario-lab": "Five-year scenario",
};

export default function Sidebar() {
  const { data } = useCatalogue();
  const location = useLocation();
  const sidebarRef = useRef<HTMLElement>(null);
  const section = data?.sections.find((candidate) => candidate.id === "capex-transmission");
  const indicatorsById = useMemo(
    () => new Map((section?.indicators ?? []).map((indicator) => [indicator.id, indicator])),
    [section],
  );
  const [activeMetric, setActiveMetric] = useState(location.hash.slice(1));

  useEffect(() => {
    setActiveMetric(location.hash.slice(1));
  }, [location.hash]);

  useEffect(() => {
    sidebarRef.current
      ?.querySelector(".sidebar-stage-link.active")
      ?.scrollIntoView({ block: "nearest" });
  }, [activeMetric]);

  useEffect(() => {
    if (!section || typeof IntersectionObserver === "undefined") return;
    const elements = section.indicators
      .map((indicator) => document.getElementById(indicator.id))
      .filter((element): element is HTMLElement => element !== null);
    if (!elements.length) return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top);
      if (visible[0]) setActiveMetric(visible[0].target.id);
    }, { rootMargin: "-18% 0px -68% 0px" });
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [section]);

  const renderMetric = (indicator: Indicator, index: number) => (
    <a
      key={indicator.id}
      className={activeMetric === indicator.id ? "sidebar-stage-link active" : "sidebar-stage-link"}
      href={`${STORY_PATH}#${indicator.id}`}
      aria-current={activeMetric === indicator.id ? "location" : undefined}
    >
      <span>{String(index + 1).padStart(2, "0")}</span>
      <strong>{shortLabels[indicator.id] ?? indicator.title}</strong>
    </a>
  );

  const returnToOverview = () => {
    setActiveMetric("");
    requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  };

  return <aside className="sidebar" ref={sidebarRef}>
    <NavLink to={STORY_PATH} className="sidebar-brand" onClick={returnToOverview}>
      <span>IC</span>
      <strong>India<br />CapEx</strong>
    </NavLink>
    <nav className="sidebar-nav" aria-label="CapEx research stages">
      <div className="sidebar-story">
        <span>Research path</span>
        <strong>Public CapEx transmission</strong>
        <p>{section?.indicators.length ?? 0} stages · {Object.keys(data?.assets ?? {}).length} datasets</p>
        <NavLink
          to={STORY_PATH}
          end
          className={!activeMetric ? "sidebar-overview active" : "sidebar-overview"}
          onClick={returnToOverview}
        >
          <i />Overview & verdict
        </NavLink>
      </div>
      {chapters.map((chapter) => {
        const indicators = chapter.ids.flatMap((id) => {
          const indicator = indicatorsById.get(id);
          return indicator ? [indicator] : [];
        });
        if (!indicators.length) return null;
        return <section className="sidebar-chapter" key={chapter.number}>
          <header><span>{chapter.number}</span><strong>{chapter.label}</strong></header>
          <div>{indicators.map((indicator) => renderMetric(
            indicator,
            section?.indicators.findIndex((candidate) => candidate.id === indicator.id) ?? 0,
          ))}</div>
        </section>;
      })}
    </nav>
    <div className="sidebar-foot"><i />Static data verified at build</div>
  </aside>;
}
