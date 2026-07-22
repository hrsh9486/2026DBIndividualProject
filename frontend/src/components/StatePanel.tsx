export function LoadingPanel() {
  return <div className="state-panel"><span className="spinner" />Loading verified data…</div>;
}

export function ErrorPanel({ message }: { message: string }) {
  return <div className="state-panel error"><strong>Data unavailable</strong><span>{message}</span></div>;
}

export function PlannedPanel({ message }: { message?: string }) {
  return <div className="state-panel"><strong>Pipeline planned</strong><span>{message ?? "The definition is locked; source ingestion and validation are not yet complete."}</span></div>;
}
