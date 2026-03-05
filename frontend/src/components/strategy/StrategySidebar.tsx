import type { StrategyListItem } from "@/types/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  strategies: StrategyListItem[];
  loading: boolean;
  selected: string | null;
  onSelect: (name: string) => void;
}

export default function StrategySidebar({
  strategies,
  loading,
  selected,
  onSelect,
}: Props) {
  return (
    <aside className="flex w-72 flex-shrink-0 flex-col border-r border-gray-800 bg-gray-900">
      <div className="flex-shrink-0 border-b border-gray-800 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">
          Strategy Builder
        </span>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-1 p-3">
          <label className="px-1 text-[11px] uppercase tracking-wide text-gray-500">
            Select Strategy
          </label>

          {loading ? (
            <div className="space-y-2 pt-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full rounded-md" />
              ))}
            </div>
          ) : strategies.length === 0 ? (
            <p className="px-1 py-3 text-xs text-gray-500">
              No strategies found. Create a strategy class in{" "}
              <code className="text-gray-400">strategies/</code> that extends{" "}
              <code className="text-gray-400">SingleAssetStrategy</code>.
            </p>
          ) : (
            strategies.map((s) => (
              <button
                key={s.class_name}
                onClick={() => onSelect(s.class_name)}
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition ${
                  selected === s.class_name
                    ? "bg-gray-800 text-white"
                    : "text-gray-300 hover:bg-gray-800/60 hover:text-white"
                }`}
              >
                <div>
                  <span className="font-medium">{s.class_name}</span>
                  <span className="ml-1.5 text-xs text-gray-500">
                    {s.module}
                  </span>
                </div>
                <span
                  className={`h-2 w-2 flex-shrink-0 rounded-full ${
                    s.has_data_spec ? "bg-blue-400" : "bg-gray-600"
                  }`}
                  title={
                    s.has_data_spec ? "Has data_spec()" : "No data_spec()"
                  }
                />
              </button>
            ))
          )}
        </div>

        {/* Help */}
        <div className="border-t border-gray-800 px-4 py-3 text-xs text-gray-500">
          <p className="mb-1.5 font-semibold text-gray-400">How it works:</p>
          <ol className="ml-3 list-decimal space-y-1">
            <li>
              Create a strategy class in{" "}
              <code className="text-gray-400">strategies/</code>
            </li>
            <li>
              Implement{" "}
              <code className="text-gray-400">data_spec()</code> to declare
              data needs
            </li>
            <li>Select it here and build data files</li>
            <li>Run backtests from the Backtest tab</li>
          </ol>
        </div>
      </ScrollArea>
    </aside>
  );
}
