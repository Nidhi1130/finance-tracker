import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardClient } from "./dashboard-client";
import { getDashboard } from "@/lib/dashboard";

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/lib/dashboard", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/dashboard")>();
  return { ...actual, getDashboard: vi.fn() };
});

import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";

const getDashboardMock = vi.mocked(getDashboard);
const useAuthMock = vi.mocked(useAuth);
const useRouterMock = vi.mocked(useRouter);

const populatedDashboard = {
  period: { from: "2026-07-01", to: "2026-07-31", bucket: "daily" as const },
  summary: { income: "1200.50", expense: "200.25", net: "1000.25" },
  categories: [
    {
      category_id: "category-a",
      name: "Groceries",
      color: "#16A34A",
      amount: "200.25",
      percentage: "100.00",
    },
  ],
  trend: [
    { period_start: "2026-07-01", label: "1 Jul", income: "1200.50", expense: "200.25" },
  ],
};

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardClient />
    </QueryClientProvider>,
  );
}

describe("DashboardClient", () => {
  beforeEach(() => {
    getDashboardMock.mockReset();
    useAuthMock.mockReturnValue({
      configured: false,
      loading: false,
      session: null,
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
    });
    useRouterMock.mockReturnValue({ push: vi.fn() } as never);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the selected period summary values", async () => {
    getDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    expect(await screen.findByText(/1\s200,50\s+kr/)).toBeInTheDocument();
    expect(screen.getByText(/200,25\s+kr/)).toBeInTheDocument();
    expect(screen.getByText(/1\s000,25\s+kr/)).toBeInTheDocument();
  });

  it("explains when the selected period has no transactions", async () => {
    getDashboardMock.mockResolvedValue({
      ...populatedDashboard,
      summary: { income: "0.00", expense: "0.00", net: "0.00" },
      categories: [],
      trend: [],
    });

    renderDashboard();

    expect(await screen.findByText("No transactions in this period")).toBeInTheDocument();
  });

  it("shows a rejected request and retries it on demand", async () => {
    getDashboardMock.mockRejectedValueOnce(new Error("Dashboard unavailable"));
    getDashboardMock.mockResolvedValueOnce(populatedDashboard);

    renderDashboard();

    expect(await screen.findByText("Dashboard unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(getDashboardMock).toHaveBeenCalledTimes(2));
  });

  it("applies the last-month preset to a new dashboard request", async () => {
    getDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    await screen.findByText(/1\s200,50\s+kr/);
    fireEvent.click(screen.getByRole("button", { name: "Last month" }));

    await waitFor(() => expect(getDashboardMock).toHaveBeenCalledTimes(2));
  });

  it("disables custom Apply until the selected dates form a valid period", () => {
    getDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    fireEvent.click(screen.getByRole("button", { name: "Custom" }));
    const applyButton = screen.getByRole("button", { name: "Apply" });

    fireEvent.change(screen.getByLabelText("Custom from date"), {
      target: { value: "" },
    });

    expect(applyButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Custom from date"), {
      target: { value: "2026-07-31" },
    });
    fireEvent.change(screen.getByLabelText("Custom to date"), {
      target: { value: "2026-07-01" },
    });

    expect(applyButton).toBeDisabled();
  });
});
