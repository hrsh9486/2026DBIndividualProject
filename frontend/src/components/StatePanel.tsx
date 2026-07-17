export function LoadingPanel() {
  return <div className="state-panel"><span className="spinner" />Loading verified data…</div>;
}

export function ErrorPanel({ message }: { message: string }) {
  return <div className="state-panel error"><strong>Data unavailable</strong><span>{message}</span></div>;
}
