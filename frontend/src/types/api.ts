// ── Data page types ──

export interface Ticker {
  symbol: string;
  status: string;
  base_asset: string;
  quote_asset: string;
  contract_type?: string;
}

export interface DataStatus {
  symbol: string;
  interval: string;
  bars: number;
  start: string;
  end: string;
  file_size: number;
  file_path: string;
}

export interface DownloadRequest {
  symbol: string;
  interval: string;
  start_date: string;
  end_date: string;
}

// ── Basis page types ──

export interface BasisRow {
  symbol: string;
  mark_price: number;
  index_price: number;
  basis_bps: number;
  funding_rate: number;
  annualized_funding: number;
  open_interest: number;
  volume_24h: number;
}

export interface BasisSnapshot {
  timestamp: string;
  rows: BasisRow[];
}

// ── Strategy page types ──

export interface StrategyListItem {
  class_name: string;
  module: string;
  has_data_spec: boolean;
}

export interface IndicatorSpec {
  name: string;
  params: Record<string, number>;
  warmup_bars: number;
}

export interface IntervalSpec {
  interval: string;
  indicators: IndicatorSpec[];
  is_price_only: boolean;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface QualityMetric {
  bars: number;
  coverage_pct: number;
  null_indicator_bars?: number;
}

export interface StrategyManifest {
  date_range: DateRange;
  built_at: string;
  quality: Record<string, QualityMetric>;
}

export interface StrategyStatus {
  class_name: string;
  spec: {
    venue: string;
    market: string;
    ticker: string;
    intervals: IntervalSpec[];
  };
  has_manifest: boolean;
  manifest: StrategyManifest | null;
  errors: string[];
}

export interface AvailableDates {
  months: string[];
  raw_earliest: string;
  earliest_start: string;
  latest_end: string;
  warmup_months: number;
  per_interval: Record<string, {
    months: string[];
    start: string;
    end: string;
    count: number;
  }>;
}

export interface BuildRequest {
  class_name: string;
  start_date: string;
  end_date: string;
}

export interface PreviewData {
  strategy_name: string;
  class_name: string;
  interval: string;
  chart_data: string; // JSON string for chart
  overlay_cols: string[];
  separate_cols: string[];
  all_cols: string[];
  table_data: Record<string, string | number>[];
  pagination: {
    page: number;
    page_size: number;
    total_rows: number;
    total_pages: number;
  };
}
