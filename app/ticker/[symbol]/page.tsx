"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { AnalyzeResult } from "@/lib/types";
import { getSignalStatus } from "@/lib/status";
import { StatusBadge } from "@/components/StatusBadge";
import { TickerChart } from "@/components/TickerChart";

export default function TickerPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = (params.symbol || "").toUpperCase();

  const [data, setData] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    fetch(`/api/analyze?ticker=${encodeURIComponent(symbol)}`)
      .then((res) => res.json().then((json) => ({ ok: res.ok, json })))
      .then(({ ok, json }) => {
        if (!ok || json.error) {
          setError(json.error || "Request failed");
          setData(null);
        } else {
          setData(json);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, [symbol]);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link href="/" className="text-sm text-ink-secondary hover:underline">
        ← Watchlist
      </Link>

      <header className="mt-4 mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{symbol}</h1>
        {data && <StatusBadge tone={getSignalStatus(data).tone} label={getSignalStatus(data).label} />}
      </header>

      {loading && <div className="rounded-lg border border-border px-4 py-8 text-center text-sm text-ink-muted">Loading…</div>}

      {error && (
        <div className="rounded-md border border-critical/30 bg-critical/10 px-4 py-3 text-sm text-critical">{error}</div>
      )}

      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Price" value={`$${data.current_price.toFixed(2)}`} />
            <Stat label="Nearest support" value={data.nearest_support ? `$${data.nearest_support.level.toFixed(2)}` : "—"} />
            <Stat label="Timeframes" value={`${data.higher_interval} / ${data.lower_interval}`} />
            <Stat label="As of" value={new Date(data.as_of).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric" })} />
          </div>

          <p className="text-sm text-ink-secondary">{data.summary}</p>

          {data.series && (
            <TickerChart series={data.series} supportResistance={data.support_resistance} divergenceSignals={data.divergence_signals} />
          )}

          <section>
            <h2 className="mb-2 text-sm font-semibold text-ink-secondary">Support / resistance (4H)</h2>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-ink-secondary">
                    <th className="px-3 py-2 font-medium">Level</th>
                    <th className="px-3 py-2 font-medium">Type</th>
                    <th className="px-3 py-2 font-medium text-right">Touches</th>
                    <th className="px-3 py-2 font-medium">Last touch</th>
                  </tr>
                </thead>
                <tbody>
                  {data.support_resistance.map((lvl, i) => (
                    <tr key={i} className="border-b border-border last:border-0">
                      <td className="px-3 py-2 tabular">${lvl.level.toFixed(2)}</td>
                      <td className="px-3 py-2 capitalize">{lvl.type}</td>
                      <td className="px-3 py-2 text-right tabular">{lvl.touches}</td>
                      <td className="px-3 py-2 text-ink-secondary">{lvl.last_touch}</td>
                    </tr>
                  ))}
                  {data.support_resistance.length === 0 && (
                    <tr>
                      <td className="px-3 py-4 text-ink-muted" colSpan={4}>
                        No levels found for this lookback window.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="mb-2 text-sm font-semibold text-ink-secondary">Divergence signals (1H)</h2>
            {data.divergence_signals.length === 0 && (
              <div className="rounded-lg border border-border px-4 py-6 text-center text-sm text-ink-muted">
                No bullish MACD divergence detected in this window.
              </div>
            )}
            <div className="space-y-3">
              {data.divergence_signals.map((sig, i) => (
                <div key={i} className="rounded-lg border border-border p-4 text-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-medium">
                      {sig.divergence.first_low.date} → {sig.divergence.second_low.date}
                    </span>
                    <StatusBadge
                      tone={sig.active_signal ? "good" : sig.triggered ? "warning" : "muted"}
                      label={sig.active_signal ? "Active buy signal" : sig.triggered ? "Triggered, unconfirmed" : "Awaiting breakout"}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-ink-secondary sm:grid-cols-4">
                    <span>
                      price: {sig.divergence.first_low.price} → {sig.divergence.second_low.price}
                    </span>
                    <span>
                      macd: {sig.divergence.first_low.macd} → {sig.divergence.second_low.macd}
                    </span>
                    <span>trigger level: {sig.trigger_line ? sig.trigger_line.level : "—"}</span>
                    <span>near support: {sig.near_support ? "yes" : "no"}</span>
                  </div>
                  {sig.breakout && (
                    <p className="mt-2 text-ink-secondary">
                      Histogram broke above trigger on {sig.breakout.date} ({sig.breakout.histogram})
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-4 py-3">
      <div className="text-xs text-ink-muted">{label}</div>
      <div className="mt-1 tabular text-lg font-semibold">{value}</div>
    </div>
  );
}
