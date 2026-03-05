import { useEffect, useRef } from "react";
import {
  createChart,
  type IChartApi,
  ColorType,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
import type { StrategyChartData } from "@/types/api";

interface Props {
  chartData: StrategyChartData;
  separateCols: string[];
}

const COLORS = [
  "#f59e0b", "#8b5cf6", "#ef4444", "#10b981", "#3b82f6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];

export default function StrategyChart({ chartData, separateCols }: Props) {
  const priceRef = useRef<HTMLDivElement>(null);
  const indicatorRef = useRef<HTMLDivElement>(null);
  const volumeRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);

  useEffect(() => {
    chartsRef.current.forEach((c) => c.remove());
    chartsRef.current = [];

    if (!chartData?.ohlcv?.length) return;

    const chartOptions = {
      layout: {
        background: { type: ColorType.Solid as const, color: "#111827" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#374151" },
      timeScale: { borderColor: "#374151", timeVisible: true },
    };

    // ── Price chart ──
    if (priceRef.current) {
      const chart = createChart(priceRef.current, {
        ...chartOptions,
        height: 300,
      });
      chartsRef.current.push(chart);

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderDownColor: "#ef4444",
        borderUpColor: "#22c55e",
        wickDownColor: "#ef4444",
        wickUpColor: "#22c55e",
      });
      candleSeries.setData(chartData.ohlcv as never[]);

      // Overlays on price chart
      let ci = 0;
      for (const [name, data] of Object.entries(chartData.overlays || {})) {
        const series = chart.addSeries(LineSeries, {
          color: COLORS[ci % COLORS.length],
          lineWidth: 1,
          title: name,
        });
        series.setData(data as never[]);
        ci++;
      }

      chart.timeScale().fitContent();
    }

    // ── Indicator chart ──
    if (indicatorRef.current && separateCols.length > 0) {
      const chart = createChart(indicatorRef.current, {
        ...chartOptions,
        height: 150,
      });
      chartsRef.current.push(chart);

      let ci = 0;
      for (const [name, data] of Object.entries(chartData.indicators || {})) {
        const series = chart.addSeries(LineSeries, {
          color: COLORS[ci % COLORS.length],
          lineWidth: 1,
          title: name,
        });
        series.setData(data as never[]);
        ci++;
      }

      chart.timeScale().fitContent();
    }

    // ── Volume chart ──
    if (volumeRef.current && chartData.volume?.length) {
      const chart = createChart(volumeRef.current, {
        ...chartOptions,
        height: 80,
      });
      chartsRef.current.push(chart);

      const volSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volSeries.setData(chartData.volume as never[]);

      chart.timeScale().fitContent();
    }

    // Sync time scales
    if (chartsRef.current.length > 1) {
      const primary = chartsRef.current[0];
      const rest = chartsRef.current.slice(1);

      primary.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) {
          rest.forEach((c) => c.timeScale().setVisibleLogicalRange(range));
        }
      });

      rest.forEach((c) => {
        c.timeScale().subscribeVisibleLogicalRangeChange((range) => {
          if (range) {
            primary.timeScale().setVisibleLogicalRange(range);
            rest
              .filter((r) => r !== c)
              .forEach((r) => r.timeScale().setVisibleLogicalRange(range));
          }
        });
      });
    }

    return () => {
      chartsRef.current.forEach((c) => c.remove());
      chartsRef.current = [];
    };
  }, [chartData, separateCols]);

  return (
    <div className="space-y-1">
      <div ref={priceRef} className="rounded bg-gray-900" />
      {separateCols.length > 0 && (
        <div ref={indicatorRef} className="rounded bg-gray-900" />
      )}
      {chartData?.volume?.length > 0 && (
        <div ref={volumeRef} className="rounded bg-gray-900" />
      )}
    </div>
  );
}
