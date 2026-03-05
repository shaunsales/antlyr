import { useState, useEffect } from "react";
import { getAvailableDates, buildStrategy } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import type { AvailableDates } from "@/types/api";

interface Props {
  className: string;
  onBuilt: () => void;
}

export default function BuildControls({ className, onBuilt }: Props) {
  const [dates, setDates] = useState<AvailableDates | null>(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [building, setBuilding] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message?: string;
  } | null>(null);

  useEffect(() => {
    setLoading(true);
    getAvailableDates(className)
      .then((d) => {
        setDates(d);
        if (d.earliest_start) setStartDate(d.earliest_start);
        if (d.latest_end) setEndDate(d.latest_end);
      })
      .finally(() => setLoading(false));
  }, [className]);

  async function handleBuild() {
    setBuilding(true);
    setResult(null);
    try {
      const res = await buildStrategy({
        class_name: className,
        start_date: startDate,
        end_date: endDate,
      });
      setResult(res);
      if (res.success) {
        setTimeout(() => onBuilt(), 1000);
      }
    } catch (e) {
      setResult({
        success: false,
        message: e instanceof Error ? e.message : "Build failed",
      });
    }
    setBuilding(false);
  }

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 space-y-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
        Build Data
      </h3>

      {loading ? (
        <p className="text-xs text-gray-500">Loading available dates...</p>
      ) : !dates ? (
        <p className="text-xs text-red-400">Failed to load available dates</p>
      ) : (
        <>
          {/* Date range inputs */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-400">
                Start Date
              </label>
              <input
                type="month"
                value={startDate}
                min={dates.earliest_start}
                max={dates.latest_end}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2.5 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-400">
                End Date
              </label>
              <input
                type="month"
                value={endDate}
                min={dates.earliest_start}
                max={dates.latest_end}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2.5 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </div>
          </div>

          {/* Available date ranges */}
          <div className="text-xs text-gray-500">
            {Object.entries(dates.per_interval).map(([iv, info]) => (
              <span key={iv} className="mr-3">
                <span className="text-gray-400">{iv}:</span>{" "}
                {info.start} → {info.end}
              </span>
            ))}
          </div>

          <Button
            onClick={handleBuild}
            disabled={building || !startDate || !endDate}
            className="w-full"
          >
            {building ? "Building..." : "Build Data"}
          </Button>

          {/* Result */}
          {result && (
            <div
              className={`rounded border p-2.5 text-xs ${
                result.success
                  ? "border-green-800 bg-green-900/30 text-green-300"
                  : "border-red-800 bg-red-900/30 text-red-300"
              }`}
            >
              {result.message || (result.success ? "Build complete!" : "Build failed")}
            </div>
          )}
        </>
      )}
    </div>
  );
}
