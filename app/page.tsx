"use client";

import { useEffect, useState } from "react";
import { WatchlistTable } from "@/components/WatchlistTable";
import type { WatchlistResult } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<WatchlistResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/watchlist");
      const json = await res.json();
      if (!res.ok || json.error) {
        setError(json.error || `Request failed (${res.status})`);
        setData(null);
      } else {
        setData(json);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">MACD Divergence Screener</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            4H support/resistance + 1H bullish MACD divergence, watchlist scan.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-ink-muted/5 disabled:opacity-50"
        >
          {loading ? "Scanning…" : "Rescan"}
        </button>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-critical/30 bg-critical/10 px-4 py-3 text-sm text-critical">
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="rounded-lg border border-border px-4 py-8 text-center text-sm text-ink-muted">
          Scanning watchlist…
        </div>
      )}

      {data && <WatchlistTable data={data} />}
    </main>
  );
}
