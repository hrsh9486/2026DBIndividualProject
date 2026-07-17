import Panel from "../../components/Panel";

export default function PendingSection({ section }) {
  return (
    <div className="max-w-2xl">
      <Panel
        title={`${section.number} — ${section.label}`}
        subtitle="No data pipeline wired up yet"
      >
        <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
          {section.blurb}.
        </p>
        <div className="mt-4 rounded-md border border-dashed border-[var(--color-border)] p-4">
          <p className="text-xs font-mono text-[var(--color-text-faint)] uppercase tracking-wide mb-2">
            To bring this bucket online
          </p>
          <ol className="text-sm text-[var(--color-text-muted)] space-y-1.5 list-decimal list-inside">
            <li>Write the source script and have it emit JSON matching a defined schema.</li>
            <li>
              Drop the output into <code className="font-mono text-[var(--color-text-primary)]">public/data/{section.id}/</code>.
            </li>
            <li>
              Build a section component under <code className="font-mono text-[var(--color-text-primary)]">src/sections/{section.id}/</code>{" "}
              and wire it into the route in place of this placeholder.
            </li>
          </ol>
        </div>
      </Panel>
    </div>
  );
}
