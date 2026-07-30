import { useEffect, useState } from "react";

type Verdict = {
  metadata: { research_question: string; classification_method: string };
  hypotheses: Array<{
    key: string;
    hypothesis: string;
    status: "supported" | "partially_supported" | "unsupported" | "inconclusive";
    interpretation: string;
    caveat: string;
  }>;
};

const LABELS = {
  supported: "Strong evidence",
  partially_supported: "Partial evidence",
  unsupported: "Little evidence",
  inconclusive: "Inconclusive",
};

export default function CapexVerdict() {
  const [payload, setPayload] = useState<Verdict | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch("/data/capex-analysis/analysis-summary.json", { cache: "no-cache" })
      .then((response) => {
        if (!response.ok) throw new Error(`Summary returned HTTP ${response.status}`);
        return response.json() as Promise<Verdict>;
      })
      .then(setPayload)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Summary unavailable"));
  }, []);
  if (error) return <section className="capex-verdict"><p>{error}</p></section>;
  if (!payload) return <section className="capex-verdict"><p>Loading hypothesis assessment…</p></section>;
  return <section id="capex-verdict" className="capex-verdict">
    <header><span>Overall assessment</span><h2>{payload.metadata.research_question}</h2></header>
    <div className="verdict-grid">
      {payload.hypotheses.map((item, index) => <article key={item.key}>
        <span>H{index + 1}</span>
        <b className={`verdict-status ${item.status}`}>{LABELS[item.status]}</b>
        <h3>{item.hypothesis}</h3>
        <p>{item.interpretation}</p>
      </article>)}
    </div>
    <p className="metric-note">{payload.metadata.classification_method}</p>
  </section>;
}
