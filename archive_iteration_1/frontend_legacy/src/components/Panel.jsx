export default function Panel({ title, subtitle, right, children, className = "" }) {
  return (
    <section
      className={`rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] ${className}`}
    >
      {(title || right) && (
        <header className="flex items-start justify-between gap-3 px-4 pt-4 pb-3 border-b border-[var(--color-border-soft)]">
          <div>
            {title && <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>}
            {subtitle && <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{subtitle}</p>}
          </div>
          {right && <div className="shrink-0">{right}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
