import type { StatusTone } from "@/lib/status";

const TONE_STYLE: Record<StatusTone, { bg: string; fg: string; icon: string }> = {
  good: { bg: "bg-good/10", fg: "text-good", icon: "✓" }, // check
  warning: { bg: "bg-warning/15", fg: "text-warning", icon: "▲" }, // triangle
  muted: { bg: "bg-ink-muted/10", fg: "text-ink-muted", icon: "–" }, // dash
};

export function StatusBadge({ tone, label }: { tone: StatusTone; label: string }) {
  const style = TONE_STYLE[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${style.bg} ${style.fg}`}
    >
      <span aria-hidden="true">{style.icon}</span>
      {label}
    </span>
  );
}
