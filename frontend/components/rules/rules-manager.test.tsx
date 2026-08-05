import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RulesManager } from "./rules-manager";
import {
  createCategorizationRule,
  deleteCategorizationRule,
  listCategorizationRules,
  updateCategorizationRule,
} from "@/lib/categorization-rules";
import { listCategories } from "@/lib/categories";

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/lib/categorization-rules", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/categorization-rules")>();
  return {
    ...actual,
    createCategorizationRule: vi.fn(),
    deleteCategorizationRule: vi.fn(),
    listCategorizationRules: vi.fn(),
    updateCategorizationRule: vi.fn(),
  };
});

vi.mock("@/lib/categories", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/categories")>();
  return { ...actual, listCategories: vi.fn() };
});

import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";

const useAuthMock = vi.mocked(useAuth);
const useRouterMock = vi.mocked(useRouter);
const listCategorizationRulesMock = vi.mocked(listCategorizationRules);
const createCategorizationRuleMock = vi.mocked(createCategorizationRule);
const updateCategorizationRuleMock = vi.mocked(updateCategorizationRule);
const deleteCategorizationRuleMock = vi.mocked(deleteCategorizationRule);
const listCategoriesMock = vi.mocked(listCategories);

const categories = [
  {
    id: "category-1",
    name: "Subscriptions",
    color: "#7C3AED",
    is_global: true,
    created_at: "2026-08-02T10:00:00Z",
  },
];

const rule = {
  id: "rule-1",
  keyword: "spotify",
  category_id: "category-1",
  category_name: "Subscriptions",
  category_color: "#7C3AED",
  enabled: true,
  created_at: "2026-08-02T10:00:00Z",
  updated_at: "2026-08-02T10:00:00Z",
};

function renderRulesManager() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <RulesManager />
      </QueryClientProvider>,
    ),
  };
}

function signedInAs(id: string) {
  useAuthMock.mockReturnValue({
    configured: true,
    loading: false,
    session: { user: { id } } as never,
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
  });
}

describe("RulesManager", () => {
  beforeEach(() => {
    listCategorizationRulesMock.mockReset();
    createCategorizationRuleMock.mockReset();
    updateCategorizationRuleMock.mockReset();
    deleteCategorizationRuleMock.mockReset();
    listCategoriesMock.mockReset();
    signedInAs("user-a");
    useRouterMock.mockReturnValue({ push: vi.fn() } as never);
    listCategoriesMock.mockResolvedValue(categories);
  });

  it("shows an authenticated user's empty rules state", async () => {
    listCategorizationRulesMock.mockResolvedValue([]);

    renderRulesManager();

    expect(await screen.findByText("No categorization rules yet.")).toBeInTheDocument();
    expect(listCategorizationRulesMock).toHaveBeenCalledTimes(1);
  });

  it("creates a rule from a keyword and category", async () => {
    listCategorizationRulesMock.mockResolvedValue([]);
    createCategorizationRuleMock.mockResolvedValue(rule);
    renderRulesManager();

    await screen.findByText("No categorization rules yet.");
    fireEvent.click(screen.getByRole("button", { name: "New rule" }));
    fireEvent.change(screen.getByLabelText("Keyword"), { target: { value: "spotify" } });
    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "category-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save rule" }));

    await waitFor(() => {
      expect(createCategorizationRuleMock).toHaveBeenCalledWith({
        keyword: "spotify",
        category_id: "category-1",
        enabled: true,
      });
    });
  });

  it("edits a rule's keyword and category", async () => {
    listCategorizationRulesMock.mockResolvedValue([rule]);
    updateCategorizationRuleMock.mockResolvedValue({ ...rule, keyword: "spotify premium" });
    renderRulesManager();

    await screen.findByText("spotify");
    fireEvent.click(screen.getByRole("button", { name: "Edit spotify" }));
    fireEvent.change(screen.getByLabelText("Keyword"), { target: { value: "spotify premium" } });
    fireEvent.click(screen.getByRole("button", { name: "Save rule" }));

    await waitFor(() => {
      expect(updateCategorizationRuleMock).toHaveBeenCalledWith("rule-1", {
        keyword: "spotify premium",
        category_id: "category-1",
        enabled: true,
      });
    });
  });

  it("disables an enabled rule", async () => {
    listCategorizationRulesMock.mockResolvedValue([rule]);
    updateCategorizationRuleMock.mockResolvedValue({ ...rule, enabled: false });
    renderRulesManager();

    await screen.findByText("spotify");
    fireEvent.click(screen.getByRole("button", { name: "Disable spotify" }));

    await waitFor(() => {
      expect(updateCategorizationRuleMock).toHaveBeenCalledWith("rule-1", { enabled: false });
    });
  });

  it("requires confirmation before deleting a rule", async () => {
    listCategorizationRulesMock.mockResolvedValue([rule]);
    deleteCategorizationRuleMock.mockResolvedValue(undefined);
    renderRulesManager();

    await screen.findByText("spotify");
    fireEvent.click(screen.getByRole("button", { name: "Delete spotify" }));
    expect(deleteCategorizationRuleMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Delete rule" }));

    await waitFor(() => expect(deleteCategorizationRuleMock).toHaveBeenCalledTimes(1));
    expect(deleteCategorizationRuleMock.mock.calls[0]?.[0]).toBe("rule-1");
  });

  it("renders validation and API errors in the rule form", async () => {
    listCategorizationRulesMock.mockResolvedValue([]);
    createCategorizationRuleMock.mockRejectedValue(new Error("Keyword already exists"));
    renderRulesManager();

    await screen.findByText("No categorization rules yet.");
    fireEvent.click(screen.getByRole("button", { name: "New rule" }));
    fireEvent.click(screen.getByRole("button", { name: "Save rule" }));
    expect(await screen.findByText("Enter a keyword and select a category.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Keyword"), { target: { value: "spotify" } });
    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "category-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save rule" }));
    expect(await screen.findByText("Keyword already exists")).toBeInTheDocument();
  });

  it("does not show user A rules while user B's rules are loading", async () => {
    listCategorizationRulesMock.mockResolvedValueOnce([rule]);
    listCategorizationRulesMock.mockImplementationOnce(() => new Promise(() => {}));
    const { queryClient, rerender } = renderRulesManager();

    await screen.findByText("spotify");
    signedInAs("user-b");
    rerender(
      <QueryClientProvider client={queryClient}>
        <RulesManager />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(listCategorizationRulesMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("spotify")).not.toBeInTheDocument();
    expect(screen.getByText("Loading categorization rules...")).toBeInTheDocument();
  });

  it("closes an open User A editor before showing User B's rules", async () => {
    listCategorizationRulesMock.mockResolvedValueOnce([rule]);
    listCategorizationRulesMock.mockResolvedValueOnce([]);
    const { queryClient, rerender } = renderRulesManager();

    await screen.findByText("spotify");
    fireEvent.click(screen.getByRole("button", { name: "Edit spotify" }));
    expect(screen.getByRole("heading", { name: "Edit rule" })).toBeInTheDocument();

    signedInAs("user-b");
    rerender(
      <QueryClientProvider client={queryClient}>
        <RulesManager />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(listCategorizationRulesMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("heading", { name: "Edit rule" })).not.toBeInTheDocument();
  });
});
