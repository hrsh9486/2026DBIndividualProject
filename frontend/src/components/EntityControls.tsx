import { countryName } from "../lib/format";

export default function EntityControls({ keys, visible, onToggle }: { keys: string[]; visible: string[]; onToggle: (key: string) => void }) {
  return <div className="entity-controls">{keys.map((key) => (
    <button key={key} className={visible.includes(key) ? "active" : ""} onClick={() => onToggle(key)}>
      <i style={{ background: `var(--series-${keys.indexOf(key) % 6})` }} />{countryName(key)}
    </button>
  ))}</div>;
}
