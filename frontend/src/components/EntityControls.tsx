import { useState } from "react";
import { seriesColor } from "../lib/seriesColors";

export default function EntityControls({ keys, visible, onToggle }: { keys: string[]; visible: string[]; onToggle: (key: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  return <div className={expanded ? "series-control expanded" : "series-control"}>
    <button className="series-disclosure" type="button" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}>
      <span>Series</span><b>{visible.length} of {keys.length} shown</b><i aria-hidden="true" />
    </button>
    <div className="entity-controls">{keys.map((key) => (
      <button type="button" key={key} className={visible.includes(key) ? "active" : ""} aria-pressed={visible.includes(key)} onClick={() => onToggle(key)}>
        <i style={{ background: seriesColor(keys.indexOf(key)) }} />{key.replaceAll("_", " ")}
      </button>
    ))}</div>
  </div>;
}
