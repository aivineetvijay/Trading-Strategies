export interface SRLevel {
  level: number;
  type: "support" | "resistance";
  touches: number;
  last_touch: string;
}

export interface DivergencePoint {
  bar_index: number;
  date: string;
  price: number;
  macd: number;
}

export interface Divergence {
  type: "bullish_divergence";
  first_low: DivergencePoint;
  second_low: DivergencePoint;
  bars_apart: number;
}

export interface TriggerLine {
  bar_index: number;
  date: string;
  level: number;
}

export interface Breakout {
  bar_index: number;
  date: string;
  histogram: number;
  trigger_level: number;
  bars_from_end: number;
}

export interface DivergenceSignal {
  divergence: Divergence;
  trigger_line: TriggerLine | null;
  breakout: Breakout | null;
  triggered: boolean;
  near_support: boolean;
  support_level: SRLevel | null;
  is_recent: boolean;
  active_signal: boolean;
}

export interface Series {
  dates: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  macd: number[];
  signal_line: number[];
  histogram: number[];
}

export interface AnalyzeResult {
  ticker: string;
  higher_interval: string;
  lower_interval: string;
  lookback: string;
  as_of: string;
  current_price: number;
  support_resistance: SRLevel[];
  nearest_support: SRLevel | null;
  divergence_signals: DivergenceSignal[];
  signal: boolean;
  summary: string;
  bars_analyzed: number;
  series?: Series;
  error?: string;
}

export interface WatchlistResult {
  signals: string[];
  results: Record<string, AnalyzeResult>;
  error?: string;
}
