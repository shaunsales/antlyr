import type { IntervalSpec } from "@/types/api";
import { Badge } from "@/components/ui/badge";

interface Props {
  intervals: IntervalSpec[];
}

export default function StrategySpec({ intervals }: Props) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Data Requirements
      </h3>
      <div className="space-y-2">
        {intervals.map((iv) => (
          <div
            key={iv.interval}
            className="flex items-center gap-3 rounded border border-gray-800 px-3 py-2 text-sm"
          >
            <span className="w-8 flex-shrink-0 font-medium text-blue-400">
              {iv.interval}
            </span>
            <div className="flex flex-1 flex-wrap gap-1.5">
              {iv.is_price_only ? (
                <span className="text-xs text-gray-500">OHLCV</span>
              ) : (
                iv.indicators.map((ind, i) => (
                  <Badge
                    key={i}
                    variant="secondary"
                    className="bg-gray-800 font-mono text-xs text-gray-300"
                  >
                    {ind.name}({Object.values(ind.params).join(",")})
                  </Badge>
                ))
              )}
            </div>
            <span className="text-xs text-gray-500">
              {iv.is_price_only
                ? "Price data only"
                : `${iv.indicators[0]?.warmup_bars ?? 0} bar warmup`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
