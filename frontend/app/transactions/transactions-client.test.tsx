import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TransactionsClient } from "./transactions-client";
import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";
import { listAccounts } from "@/lib/accounts";
import { listCategories } from "@/lib/categories";
import { createCategorizationRule } from "@/lib/categorization-rules";
import {
  deleteTransaction,
  listTransactions,
  retryCategorization,
  saveTransaction,
} from "@/lib/transactions";
import type { Transaction } from "@/lib/transactions";

vi.mock("@/components/auth/auth-provider", () => ({
  useAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

vi.mock("@/lib/accounts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/accounts")>();
  return { ...actual, listAccounts: vi.fn() };
});

vi.mock("@/lib/categories", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/categories")>();
  return { ...actual, listCategories: vi.fn() };
});

vi.mock("@/lib/categorization-rules", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/categorization-rules")>();
  return { ...actual, createCategorizationRule: vi.fn() };
});

vi.mock("@/lib/transactions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/transactions")>();
  return {
    ...actual,
    deleteTransaction: vi.fn(),
    listTransactions: vi.fn(),
    retryCategorization: vi.fn(),
    saveTransaction: vi.fn(),
  };
});

const useAuthMock = vi.mocked(useAuth);
const useRouterMock = vi.mocked(useRouter);
const listAccountsMock = vi.mocked(listAccounts);
const listCategoriesMock = vi.mocked(listCategories);
const createCategorizationRuleMock = vi.mocked(createCategorizationRule);
const deleteTransactionMock = vi.mocked(deleteTransaction);
const listTransactionsMock = vi.mocked(listTransactions);
const retryCategorizationMock = vi.mocked(retryCategorization);
const saveTransactionMock = vi.mocked(saveTransaction);

const categories = [
  {
    id: "category-1",
    name: "Subscriptions",
    color: "#7C3AED",
    is_global: true,
    created_at: "2026-08-02T10:00:00Z",
  },
  {
    id: "category-2",
    name: "Entertainment",
    color: "#2563EB",
    is_global: true,
    created_at: "2026-08-02T10:00:00Z",
  },
];

const accounts = [
  {
    id: "account-1",
    name: "Checking",
    created_at: "2026-08-02T10:00:00Z",
  },
];

function transaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: "transaction-1",
    amount: "12.50",
    type: "expense",
    description: "Spotify Premium",
    date: "2026-08-02",
    category_id: "category-1",
    account_id: "account-1",
    category_source: "rule",
    categorization_status: "categorized",
    categorized_at: "2026-08-02T10:01:00Z",
    created_at: "2026-08-02T10:00:00Z",
    updated_at: "2026-08-02T10:01:00Z",
    ...overrides,
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

function renderTransactionsClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <TransactionsClient />
      </QueryClientProvider>,
    ),
  };
}

async function editCategory(categoryId: string) {
  fireEvent.click(await screen.findByRole("button", { name: "Edit" }));
  fireEvent.change(screen.getByLabelText("Category"), { target: { value: categoryId } });
  fireEvent.click(screen.getByRole("button", { name: "Update transaction" }));
}

describe("TransactionsClient Phase 4 categorization", () => {
  beforeEach(() => {
    vi.useRealTimers();
    signedInAs("user-a");
    useRouterMock.mockReturnValue({ push: vi.fn() } as never);
    listTransactionsMock.mockReset();
    saveTransactionMock.mockReset();
    deleteTransactionMock.mockReset();
    retryCategorizationMock.mockReset();
    createCategorizationRuleMock.mockReset();
    listCategoriesMock.mockReset();
    listAccountsMock.mockReset();
    listCategoriesMock.mockResolvedValue(categories);
    listAccountsMock.mockResolvedValue(accounts);
    deleteTransactionMock.mockResolvedValue(undefined);
  });

  it("labels the empty category choice as Auto categorize", async () => {
    listTransactionsMock.mockResolvedValue([]);

    renderTransactionsClient();

    expect(await screen.findByRole("option", { name: "Auto categorize" })).toBeInTheDocument();
  });

  it("shows a stable pending row and polls every 1.5 seconds only while pending", async () => {
    vi.useFakeTimers();
    listTransactionsMock
      .mockResolvedValueOnce(
        [
          transaction({
            category_id: null,
            category_source: null,
            categorization_status: "pending",
            categorized_at: null,
          }),
        ],
      )
      .mockResolvedValueOnce(
        [
          transaction({
            category_id: null,
            category_source: null,
            categorization_status: "pending",
            categorized_at: null,
          }),
        ],
      )
      .mockResolvedValue([transaction({ category_source: "openai" })]);

    renderTransactionsClient();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(screen.getByText("Categorizing…")).toBeInTheDocument();
    expect(screen.getByText("Spotify Premium").closest("tr")).toBeInTheDocument();
    expect(listTransactionsMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(listTransactionsMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(listTransactionsMock).toHaveBeenCalledTimes(3);
    await vi.waitFor(() => {
      expect(screen.queryByText("Categorizing…")).not.toBeInTheDocument();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4500);
    });
    expect(listTransactionsMock).toHaveBeenCalledTimes(3);
  });

  it("names rule and OpenAI automatic category sources accessibly", async () => {
    listTransactionsMock.mockResolvedValue([
      transaction({ id: "rule-transaction", description: "Rule result", category_source: "rule" }),
      transaction({
        id: "openai-transaction",
        description: "OpenAI result",
        category_source: "openai",
      }),
    ]);

    renderTransactionsClient();

    expect(
      await screen.findByLabelText("Automatically categorized by saved rule"),
    ).toHaveTextContent("Auto");
    expect(screen.getByLabelText("Automatically categorized by OpenAI")).toHaveTextContent(
      "Auto",
    );
  });

  it("does not show an Auto badge for a manual category", async () => {
    listTransactionsMock.mockResolvedValue([
      transaction({ category_source: "manual", description: "Manual result" }),
    ]);

    renderTransactionsClient();

    await screen.findByText("Manual result");
    expect(screen.queryByText("Auto")).not.toBeInTheDocument();
  });

  it("keeps a failed transaction uncategorized and retries it through the action", async () => {
    const failed = transaction({
      category_id: null,
      category_source: null,
      categorization_status: "failed",
      categorized_at: null,
      description: "Failed item",
    });
    listTransactionsMock.mockResolvedValue([failed]);
    retryCategorizationMock.mockResolvedValue({
      ...failed,
      categorization_status: "pending",
    });

    renderTransactionsClient();

    const row = (await screen.findByText("Failed item")).closest("tr");
    expect(row).not.toBeNull();
    expect(within(row as HTMLTableRowElement).getByText("Uncategorized")).toBeInTheDocument();
    fireEvent.click(within(row as HTMLTableRowElement).getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(retryCategorizationMock).toHaveBeenCalledWith("transaction-1"));
  });

  it("saves an automatic category correction before offering explicit rule creation", async () => {
    const automatic = transaction();
    listTransactionsMock.mockResolvedValue([automatic]);
    saveTransactionMock.mockImplementation(async () => {
      expect(createCategorizationRuleMock).not.toHaveBeenCalled();
      return transaction({ category_id: "category-2", category_source: "manual" });
    });
    createCategorizationRuleMock.mockResolvedValue({
      id: "rule-1",
      keyword: "spotify premium",
      category_id: "category-2",
      category_name: "Entertainment",
      category_color: "#2563EB",
      enabled: true,
      created_at: "2026-08-02T10:02:00Z",
      updated_at: "2026-08-02T10:02:00Z",
    });
    renderTransactionsClient();

    await editCategory("category-2");

    expect(await screen.findByRole("heading", { name: "Save this as a rule" })).toBeInTheDocument();
    expect(saveTransactionMock).toHaveBeenCalledWith(
      "transaction-1",
      expect.objectContaining({ category_id: "category-2" }),
    );
    expect(screen.getByLabelText("Keyword")).toHaveValue("spotify premium");
    expect(createCategorizationRuleMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Save rule" }));

    await waitFor(() => {
      expect(createCategorizationRuleMock).toHaveBeenCalledWith({
        keyword: "spotify premium",
        category_id: "category-2",
        enabled: true,
      });
    });
  });

  it("dismisses the rule offer without undoing the saved correction", async () => {
    listTransactionsMock.mockResolvedValue([transaction()]);
    saveTransactionMock.mockResolvedValue(
      transaction({ category_id: "category-2", category_source: "manual" }),
    );
    renderTransactionsClient();

    await editCategory("category-2");
    expect(await screen.findByRole("heading", { name: "Save this as a rule" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Save this as a rule" })).not.toBeInTheDocument();
    });
    expect(saveTransactionMock).toHaveBeenCalledTimes(1);
    expect(createCategorizationRuleMock).not.toHaveBeenCalled();
  });

  it("does not offer a rule after correcting an automatic transaction without a description", async () => {
    listTransactionsMock.mockResolvedValue([transaction({ description: null })]);
    saveTransactionMock.mockResolvedValue(
      transaction({ description: null, category_id: "category-2", category_source: "manual" }),
    );
    renderTransactionsClient();

    await editCategory("category-2");

    await waitFor(() => expect(saveTransactionMock).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("heading", { name: "Save this as a rule" })).not.toBeInTheDocument();
  });

  it("does not display user A transactions while user B transactions are loading", async () => {
    listTransactionsMock.mockResolvedValueOnce([
      transaction({ description: "User A private transaction" }),
    ]);
    listTransactionsMock.mockImplementationOnce(() => new Promise(() => {}));
    const { queryClient, rerender } = renderTransactionsClient();

    await screen.findByText("User A private transaction");
    signedInAs("user-b");
    rerender(
      <QueryClientProvider client={queryClient}>
        <TransactionsClient />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(listTransactionsMock).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("User A private transaction")).not.toBeInTheDocument();
    expect(screen.getByText("Loading transactions...")).toBeInTheDocument();
  });
});
