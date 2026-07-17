"use client";

import Link from "next/link";
import type { WatchlistResult } from "@/lib/types";
import { getSignalStatus } from "@/lib/status";
import { StatusBadge } from "./StatusBadge";

export function WatchlistTable({ data }: { data: WatchlistResult }) {
  const tickers = Object.keys(data.results);

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-ink-secondary">
            <th className="px-4 py-3 font-medium">Ticker</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium text-right tabular">Price</th>
            <th className="px-4 py-3 font-medium text-right tabular">Nearest support</th>
            <th className="px-4 py-3 font-medium">Summary</th>
          </tr>
        </thead>
        <tbody>
          {tickers.map((ticker) => {
            const result = data.results[ticker];
            if (result.error) {
              return (
                <tr key={ticker} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/ticker/${ticker}`} className="hover:underline">
                      {ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3" colSpan={4}>
                    <span className="text-ink-muted">{result.error}</span>
                  </td>
                </tr>
              );
            }
            const status = getSignalStatus(result);
            return (
              <tr key={ticker} className="border-b border-border last:border-0 hover:bg-ink-muted/5">
                <td className="px-4 py-3 font-medium">
                  <Link href={`/ticker/${ticker}`} className="hover:underline">
                    {ticker}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge tone={status.tone} label={status.label} />
                </td>
                <td className="px-4 py-3 text-right tabular">${result.current_price.toFixed(2)}</td>
                <td className="px-4 py-3 text-right tabular text-ink-secondary">
                  {result.nearest_support ? `$${result.nearest_support.level.toFixed(2)}` : "—"}
                </td>
                <td className="px-4 py-3 text-ink-secondary">{result.summary}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
