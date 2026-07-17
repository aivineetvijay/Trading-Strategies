"use client";

import { useMemo, useRef, useState } from "react";
import type { DivergenceSignal, SRLevel, Series } from "@/lib/types";

const WIDTH = 900;
const PRICE_HEIGHT = 280;
const MACD_HEIGHT = 160;
const GAP = 28;
const PAD_LEFT = 56;
const PAD_RIGHT = 64;
const PAD_TOP = 16;
const PRICE_PANEL_BOTTOM = PAD_TOP + PRICE_HEIGHT;
const MACD_PANEL_TOP = PRICE_PANEL_BOTTOM + GAP;
const MACD_PANEL_BOTTOM = MACD_PANEL_TOP + MACD_HEIGHT;
const TOTAL_HEIGHT = MACD_PANEL_BOTTOM + 32;
const PLOT_LEFT = PAD_LEFT;
const PLOT_RIGHT = WIDTH - PAD_RIGHT;

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric" });
}

export function TickerChart({
  series,
  supportResistance,
  divergenceSignals,
}: {
  series: Series;
  supportResistance: SRLevel[];
  divergenceSignals: DivergenceSignal[];
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const n = series.dates.length;

  const { xScale, priceScale, macdScale } = useMemo(() => {
    const xScale = (i: number) => PLOT_LEFT + (n <= 1 ? 0 : (i / (n - 1)) * (PLOT_RIGHT - PLOT_LEFT));

    const levelValues = supportResistance.map((l) => l.level);
    const priceMin = Math.min(...series.low, ...levelValues);
    const priceMax = Math.max(...series.high, ...levelValues);
    const pricePad = (priceMax - priceMin) * 0.08 || 1;
    const priceLo = priceMin - pricePad;
    const priceHi = priceMax + pricePad;
    const priceScale = (v: number) =>
      PRICE_PANEL_BOTTOM - ((v - priceLo) / (priceHi - priceLo || 1)) * PRICE_HEIGHT;

    const macdAbsMax =
      Math.max(
        1e-6,
        ...series.histogram.map(Math.abs),
        ...series.macd.map(Math.abs),
        ...divergenceSignals.map((s) => Math.abs(s.trigger_line?.level ?? 0)),
      ) * 1.15;
    const macdScale = (v: number) => MACD_PANEL_TOP + MACD_HEIGHT / 2 - (v / macdAbsMax) * (MACD_HEIGHT / 2);

    return { xScale, priceScale, macdScale };
  }, [series, supportResistance, divergenceSignals, n]);

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * WIDTH;
    const frac = (px - PLOT_LEFT) / (PLOT_RIGHT - PLOT_LEFT);
    const idx = Math.round(frac * (n - 1));
    setHoverIdx(Math.max(0, Math.min(n - 1, idx)));
  }

  const closePath = series.close.map((v, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${priceScale(v)}`).join(" ");
  const barWidth = Math.max(1, ((PLOT_RIGHT - PLOT_LEFT) / n) * 0.6);
  const zeroY = macdScale(0);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${TOTAL_HEIGHT}`}
        className="w-full"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* panel backgrounds */}
        <rect x={PLOT_LEFT} y={PAD_TOP} width={PLOT_RIGHT - PLOT_LEFT} height={PRICE_HEIGHT} fill="none" />
        <line x1={PLOT_LEFT} y1={PRICE_PANEL_BOTTOM} x2={PLOT_RIGHT} y2={PRICE_PANEL_BOTTOM} stroke="var(--gridline)" />

        {/* support/resistance reference lines */}
        {supportResistance.map((lvl, i) => {
          const y = priceScale(lvl.level);
          const color = lvl.type === "support" ? "var(--status-good)" : "var(--status-critical)";
          return (
            <g key={`sr-${i}`}>
              <line
                x1={PLOT_LEFT}
                x2={PLOT_RIGHT}
                y1={y}
                y2={y}
                stroke={color}
                strokeWidth={1}
                strokeDasharray="4 3"
                opacity={0.55}
              />
              <text x={PLOT_RIGHT + 4} y={y + 3} fontSize={10} fill={color}>
                {lvl.type === "support" ? "S" : "R"} {lvl.level.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* price line */}
        <path d={closePath} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" />

        {/* divergence trough markers + connecting line */}
        {divergenceSignals.map((sig, i) => {
          const { first_low, second_low } = sig.divergence;
          const x1 = xScale(first_low.bar_index);
          const y1 = priceScale(first_low.price);
          const x2 = xScale(second_low.bar_index);
          const y2 = priceScale(second_low.price);
          return (
            <g key={`div-${i}`}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--series-2)" strokeWidth={1.5} strokeDasharray="2 2" />
              <circle cx={x1} cy={y1} r={4} fill="var(--surface-1)" stroke="var(--series-2)" strokeWidth={2} />
              <circle cx={x2} cy={y2} r={4} fill="var(--surface-1)" stroke="var(--series-2)" strokeWidth={2} />
              <text x={x2} y={y2 + 16} fontSize={10} fill="var(--series-2)" textAnchor="middle">
                bullish div
              </text>
            </g>
          );
        })}

        {/* MACD panel */}
        <line x1={PLOT_LEFT} y1={zeroY} x2={PLOT_RIGHT} y2={zeroY} stroke="var(--baseline)" strokeWidth={1} />
        {series.histogram.map((h, i) => {
          const x = xScale(i);
          const y0 = zeroY;
          const y1 = macdScale(h);
          const top = Math.min(y0, y1);
          const height = Math.max(1, Math.abs(y1 - y0));
          return (
            <rect
              key={`hist-${i}`}
              x={x - barWidth / 2}
              y={top}
              width={barWidth}
              height={height}
              fill={h >= 0 ? "var(--series-1)" : "var(--status-critical)"}
              opacity={0.85}
            />
          );
        })}

        {/* trigger lines + breakout markers */}
        {divergenceSignals.map((sig, i) => {
          if (!sig.trigger_line) return null;
          const y = macdScale(sig.trigger_line.level);
          const startX = xScale(sig.trigger_line.bar_index);
          const endIdx = sig.breakout ? sig.breakout.bar_index : n - 1;
          const endX = xScale(endIdx);
          return (
            <g key={`trigger-${i}`}>
              <line x1={startX} x2={endX} y1={y} y2={y} stroke="var(--series-2)" strokeWidth={1.5} strokeDasharray="4 3" />
              <text x={startX} y={y - 5} fontSize={10} fill="var(--series-2)">
                trigger
              </text>
              {sig.breakout && (
                <g>
                  <circle
                    cx={xScale(sig.breakout.bar_index)}
                    cy={macdScale(sig.breakout.histogram)}
                    r={5}
                    fill="var(--status-good)"
                  />
                  <text
                    x={xScale(sig.breakout.bar_index)}
                    y={macdScale(sig.breakout.histogram) - 10}
                    fontSize={10}
                    fontWeight={600}
                    fill="var(--status-good)"
                    textAnchor="middle"
                  >
                    buy
                  </text>
                </g>
              )}
            </g>
          );
        })}

        {/* hover crosshair */}
        {hoverIdx !== null && (
          <g>
            <line
              x1={xScale(hoverIdx)}
              x2={xScale(hoverIdx)}
              y1={PAD_TOP}
              y2={MACD_PANEL_BOTTOM}
              stroke="var(--text-muted)"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            <circle cx={xScale(hoverIdx)} cy={priceScale(series.close[hoverIdx])} r={3.5} fill="var(--series-1)" />
          </g>
        )}
      </svg>

      {hoverIdx !== null && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 rounded-md border border-border px-3 py-2 text-xs text-ink-secondary">
          <span className="font-medium text-ink-primary">{fmtDate(series.dates[hoverIdx])}</span>
          <span>close ${series.close[hoverIdx].toFixed(2)}</span>
          <span>macd {series.macd[hoverIdx].toFixed(3)}</span>
          <span>signal {series.signal_line[hoverIdx].toFixed(3)}</span>
          <span>hist {series.histogram[hoverIdx].toFixed(3)}</span>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-3" style={{ background: "var(--series-1)" }} /> price
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-3 border-t border-dashed" style={{ borderColor: "var(--status-good)" }} />{" "}
          support
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-3 border-t border-dashed" style={{ borderColor: "var(--status-critical)" }} />{" "}
          resistance
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-0.5 w-3 border-t border-dashed" style={{ borderColor: "var(--series-2)" }} />{" "}
          divergence / trigger line
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "var(--status-good)" }} /> buy signal
        </span>
      </div>
    </div>
  );
}
