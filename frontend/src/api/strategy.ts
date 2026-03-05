import { get, post } from "./client";
import type {
  StrategyListItem,
  StrategyStatus,
  AvailableDates,
  BuildRequest,
  PreviewData,
} from "@/types/api";

export function listStrategies(): Promise<StrategyListItem[]> {
  return get<{ strategies: StrategyListItem[] }>("/strategy/").then(
    (r) => r.strategies
  );
}

export function getStrategySpec(className: string): Promise<StrategyStatus> {
  return get<StrategyStatus>(`/strategy/spec/${className}`);
}

export function getAvailableDates(className: string): Promise<AvailableDates> {
  return get<AvailableDates>(`/strategy/available-dates/${className}`);
}

export function buildStrategy(req: BuildRequest): Promise<{ success: boolean; message?: string }> {
  return post("/strategy/build", req);
}

export function deleteStrategy(className: string): Promise<{ success: boolean }> {
  return post("/strategy/delete", { class_name: className });
}

export function getPreview(
  className: string,
  interval: string,
  page = 1,
  pageSize = 100
): Promise<PreviewData> {
  return get<PreviewData>(
    `/strategy/preview/${className}/${interval}?page=${page}&page_size=${pageSize}`
  );
}
