import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <DashboardClient />
      </QueryClientProvider>,
    ),
  };
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

    expect((await screen.findAllByText(/1\s200,50\s+kr/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/200,25\s+kr/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/1\s000,25\s+kr/).length).toBeGreaterThan(0);
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
    expect(screen.getByText("No expense categories in this period")).toBeInTheDocument();
    expect(screen.getByText("No cash-flow activity in this period")).toBeInTheDocument();
  });

  it("labels the populated chart cards with their headings", async () => {
    getDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    expect(await screen.findByRole("heading", { name: "Expense categories" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cash flow" })).toBeInTheDocument();
  });

  it("shows a rejected request and retries it on demand", async () => {
    getDashboardMock.mockRejectedValueOnce(new Error("Dashboard unavailable"));
    getDashboardMock.mockResolvedValueOnce(populatedDashboard);

    renderDashboard();

    expect(await screen.findByText("Dashboard unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(getDashboardMock).toHaveBeenCalledTimes(2));
  });

  it("applies the exact previous-month boundaries for the Last month preset", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 6, 15));
    getDashboardMock.mockResolvedValue(populatedDashboard);

    renderDashboard();

    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Last month" }));
    await act(async () => {});

    expect(getDashboardMock).toHaveBeenLastCalledWith("2026-06-01", "2026-06-30");
  });

  it("does not show user A data while user B dashboard data is pending", async () => {
    useAuthMock.mockReturnValue({
      configured: true,
      loading: false,
      session: { user: { id: "user-a" } } as never,
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
    });
    getDashboardMock.mockResolvedValueOnce(populatedDashboard);
    getDashboardMock.mockImplementationOnce(() => new Promise(() => {}));

    const { queryClient, rerender } = renderDashboard();

    expect((await screen.findAllByText(/1\s200,50\s+kr/)).length).toBeGreaterThan(0);

    useAuthMock.mockReturnValue({
      configured: true,
      loading: false,
      session: { user: { id: "user-b" } } as never,
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <DashboardClient />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(getDashboardMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(/1\s200,50\s+kr/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Loading dashboard")).toBeInTheDocument();
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
