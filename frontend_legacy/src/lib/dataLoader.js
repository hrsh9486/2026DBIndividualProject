import { useEffect, useState } from "react";

/**
 * Loads a static JSON file from /public/data/<section>/<file>.json.
 * Each script's output should be copied/symlinked into that folder.
 *
 * Usage: const { data, loading, error } = useJson("currency", "rebased_performance");
 */
export function useJson(section, file) {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });

    fetch(`/data/${section}/${file}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`${file}.json — HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setState({ data: json, loading: false, error: null });
      })
      .catch((err) => {
        if (!cancelled) setState({ data: null, loading: false, error: err.message });
      });

    return () => {
      cancelled = true;
    };
  }, [section, file]);

  return state;
}

/**
 * Loads several JSON files for a section in parallel.
 * Usage: const { data, loading, error } = useJsonBundle("currency", ["rebased_performance", "volatility_summary"]);
 * data is keyed by file name.
 */
export function useJsonBundle(section, files) {
  const [state, setState] = useState({ data: {}, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    setState({ data: {}, loading: true, error: null });

    Promise.all(
      files.map((file) =>
        fetch(`/data/${section}/${file}.json`).then((res) => {
          if (!res.ok) throw new Error(`${file}.json — HTTP ${res.status}`);
          return res.json().then((json) => [file, json]);
        })
      )
    )
      .then((entries) => {
        if (cancelled) return;
        setState({ data: Object.fromEntries(entries), loading: false, error: null });
      })
      .catch((err) => {
        if (!cancelled) setState({ data: {}, loading: false, error: err.message });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, files.join(",")]);

  return state;
}
