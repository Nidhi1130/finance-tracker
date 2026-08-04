import { requestJson } from "./api";

export type DashboardBucket = "daily" | "weekly" | "monthly";

export interface DashboardResponse {
  period: { from: string; to: string; bucket: DashboardBucket };
  summary: { income: string; expense: string; net: string };
  categories: Array<{
    category_id: string | null;
    name: string;
    color: string;
    amount: string;
    percentage: string;
  }>;
  trend: Array<{
    period_start: string;
    label: string;
    income: string;
    expense: string;
  }>;
}

export interface DashboardPeriodPreset {
  from: string;
  to: string;
}

export function dateToInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function thisMonthPeriod(now: Date): DashboardPeriodPreset {
  const year = now.getFullYear();
  const month = now.getMonth();
  return {
    from: dateToInputValue(new Date(year, month, 1)),
    to: dateToInputValue(new Date(year, month + 1, 0)),
  };
}

export function lastMonthPeriod(now: Date): DashboardPeriodPreset {
  const year = now.getFullYear();
  const month = now.getMonth();
  return {
    from: dateToInputValue(new Date(year, month - 1, 1)),
    to: dateToInputValue(new Date(year, month, 0)),
  };
}

export function dashboardQueryKey(userId: string, from: string, to: string) {
  return ["dashboard", userId, from, to] as const;
}

export async function getDashboard(from: string, to: string): Promise<DashboardResponse> {
  const query = new URLSearchParams({ from, to });
  return requestJson<DashboardResponse>(`/dashboard?${query.toString()}`);
}
