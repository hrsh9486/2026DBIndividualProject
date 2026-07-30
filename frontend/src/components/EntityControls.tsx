import { countryName } from "../lib/format";
import { seriesColor } from "../lib/seriesColors";

export default function EntityControls({ keys, visible, onToggle }: { keys: string[]; visible: string[]; onToggle: (key: string) => void }) {
  return <div className="entity-controls">{keys.map((key) => (
    <button key={key} className={visible.includes(key) ? "active" : ""} onClick={() => onToggle(key)}>
      <i style={{ background: seriesColor(keys.indexOf(key)) }} />{countryName(key)}
    </button>
  ))}</div>;
}
