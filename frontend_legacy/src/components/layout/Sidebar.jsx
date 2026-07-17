import { NavLink } from "react-router-dom";
import { SECTIONS } from "../../lib/sections";

export default function Sidebar() {
  return (
    <aside className="hidden md:flex md:w-72 md:flex-col border-r border-[var(--color-border)] bg-[var(--color-ink-900)]">
      <div className="px-5 pt-6 pb-5 border-b border-[var(--color-border-soft)]">
        <div className="font-mono text-[11px] tracking-[0.2em] text-[var(--color-marigold)] uppercase">
          Position Tracker
        </div>
        <div className="mt-1 text-lg font-semibold leading-tight">India</div>
        <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Markets · Macro · Structure
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {SECTIONS.map((s) => (
          <NavLink
            key={s.id}
            to={`/${s.id}`}
            className={({ isActive }) =>
              [
                "group flex items-start gap-3 px-5 py-3 border-l-2 transition-colors",
                isActive
                  ? "border-[var(--color-marigold)] bg-[var(--color-panel)]"
                  : "border-transparent hover:bg-[var(--color-panel)]/60",
              ].join(" ")
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={[
                    "font-mono text-[11px] mt-0.5 tabular-figures",
                    isActive ? "text-[var(--color-marigold)]" : "text-[var(--color-text-faint)]",
                  ].join(" ")}
                >
                  {s.number}
                </span>
                <span className="flex-1 min-w-0">
                  <span
                    className={[
                      "block text-sm font-medium",
                      isActive ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)]",
                    ].join(" ")}
                  >
                    {s.label}
                  </span>
                  <span className="block text-xs text-[var(--color-text-faint)] mt-0.5 leading-snug line-clamp-2">
                    {s.blurb}
                  </span>
                </span>
                {s.status === "pending" && (
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-[var(--color-text-faint)]" title="Data pipeline pending" />
                )}
                {s.status === "live" && (
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" title="Live data" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-[var(--color-border-soft)] font-mono text-[10px] text-[var(--color-text-faint)] uppercase tracking-wide">
        7 buckets · sources: WB · FRED · IMF · RBI DBIE
      </div>
    </aside>
  );
}
