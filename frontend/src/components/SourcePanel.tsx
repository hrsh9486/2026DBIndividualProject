import { useState } from "react";
import type { StaticPayload } from "../data/types";

export default function SourcePanel({ payload }: { payload: StaticPayload }) {
  const [expanded, setExpanded] = useState(false);
  const metadata = payload.metadata as Record<string, unknown>;
  const source = Array.isArray(metadata.source)
    ? metadata.source.map((item) => (item as { name?: string }).name).filter(Boolean).join(", ")
    : String(metadata.source ?? "Not specified");
  return (
    <aside className={expanded ? "source-panel expanded" : "source-panel"}>
      <button className="source-disclosure" type="button" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}>
        <span>Source & methodology</span><i aria-hidden="true" />
      </button>
      <div className="source-panel-content">
        <div><span>Source</span><strong>{source}</strong></div>
        <div><span>Frequency</span><strong>{String(metadata.frequency ?? metadata.interval ?? "Mixed")}</strong></div>
        <div><span>Method</span><strong>{String(metadata.methodology ?? (metadata.is_derived ? "Derived series" : "Published observation"))}</strong></div>
      </div>
    </aside>
  );
}
