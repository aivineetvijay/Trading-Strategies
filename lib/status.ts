import type { AnalyzeResult } from "./types";

export type StatusTone = "good" | "warning" | "muted";

export interface SignalStatus {
  tone: StatusTone;
  label: string;
}

/** Classify a ticker's overall state from its analyze_ticker result.
 * Mirrors the strategy's own precedence: an active_signal (steps 1-4 all
 * confirmed) beats a plain trigger-line breakout, which beats a divergence
 * that's still waiting on the histogram to break its trigger line. */
export function getSignalStatus(result: AnalyzeResult): SignalStatus {
  if (result.error) {
    return { tone: "muted", label: "Error" };
  }
  if (result.signal) {
    return { tone: "good", label: "Buy signal" };
  }
  const anyTriggered = result.divergence_signals.some((s) => s.triggered);
  if (anyTriggered) {
    return { tone: "warning", label: "Breakout, unconfirmed" };
  }
  if (result.divergence_signals.length > 0) {
    return { tone: "warning", label: "Divergence forming" };
  }
  return { tone: "muted", label: "No setup" };
}
