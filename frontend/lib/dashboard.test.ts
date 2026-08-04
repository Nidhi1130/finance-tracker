import { beforeEach, describe, expect, it, vi } from "vitest";
import { requestJson } from "./api";
import {
  dashboardQueryKey,
  dateToInputValue,
  getDashboard,
  lastMonthPeriod,
  thisMonthPeriod,
} from "./dashboard";

vi.mock("./api", () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe("dashboard calendar and API helpers", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("formats dates from the local calendar", () => {
    expect(dateToInputValue(new Date(2026, 6, 5))).toBe("2026-07-05");
  });

  it("returns the full local current-month period", () => {
    expect(thisMonthPeriod(new Date(2026, 6, 15))).toEqual({
      from: "2026-07-01",
      to: "2026-07-31",
    });
  });

  it("returns the prior-year December period when last month crosses January", () => {
    expect(lastMonthPeriod(new Date(2026, 0, 15))).toEqual({
      from: "2025-12-01",
      to: "2025-12-31",
    });
  });

  it("scopes the dashboard cache key to the user and applied period", () => {
    expect(dashboardQueryKey("user-a", "2026-07-01", "2026-07-31")).toEqual([
      "dashboard",
      "user-a",
      "2026-07-01",
      "2026-07-31",
    ]);
  });

  it("requests the dashboard endpoint for the selected period", async () => {
    requestJsonMock.mockResolvedValue({
      period: { from: "2026-07-01", to: "2026-07-31", bucket: "daily" },
      summary: { income: "0.00", expense: "0.00", net: "0.00" },
      categories: [],
      trend: [],
    });

    await getDashboard("2026-07-01", "2026-07-31");

    expect(requestJsonMock).toHaveBeenCalledWith(
      "/dashboard?from=2026-07-01&to=2026-07-31",
    );
  });
});
