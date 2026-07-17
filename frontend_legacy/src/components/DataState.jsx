export function LoadingBlock({ label = "Loading data" }) {
  return (
    <div className="flex items-center gap-2 py-8 justify-center text-[var(--color-text-faint)] font-mono text-xs">
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-marigold)] animate-pulse" />
      {label}…
    </div>
  );
}

export function ErrorBlock({ message }) {
  return (
    <div className="py-6 px-4 rounded-md border border-[var(--color-brick-dim)] bg-[var(--color-brick-dim)]/10">
      <p className="text-sm text-[var(--color-brick)] font-medium">Couldn't load this dataset.</p>
      <p className="text-xs text-[var(--color-text-muted)] mt-1 font-mono">{message}</p>
      <p className="text-xs text-[var(--color-text-faint)] mt-2">
        Check that the source script has written its JSON into <code>public/data/…</code> and that the filename matches.
      </p>
    </div>
  );
}
