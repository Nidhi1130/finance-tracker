import { beforeEach, describe, expect, it, vi } from "vitest";
import { requestJson } from "./api";
import {
  deleteTransaction,
  listTransactions,
  retryCategorization,
  saveTransaction,
  suggestRuleKeyword,
  transactionQueryKey,
} from "./transactions";
import type { Transaction, TransactionFilters, TransactionPayload } from "./transactions";

vi.mock("./api", () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

const filters: TransactionFilters = {
  from: "2026-08-01",
  to: "2026-08-31",
  type: "expense",
  categoryId: "category/one",
  accountId: "account one",
};

const transaction: Transaction = {
  id: "transaction-1",
  amount: "12.50",
  type: "expense",
  description: "Spotify Premium",
  date: "2026-08-02",
  category_id: "category-1",
  account_id: "account-1",
  category_source: "openai",
  categorization_status: "categorized",
  categorized_at: "2026-08-02T10:00:00Z",
  created_at: "2026-08-02T09:59:00Z",
  updated_at: "2026-08-02T10:00:00Z",
};

const payload: TransactionPayload = {
  amount: "12.50",
  type: "expense",
  date: "2026-08-02",
  description: "Spotify Premium",
  category_id: "category-1",
  account_id: "account-1",
};

describe("transaction API client", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("scopes a filtered transaction cache key to the authenticated user", () => {
    expect(transactionQueryKey("user-a", filters)).toEqual([
      "transactions",
      "user-a",
      filters,
    ]);
  });

  it("encodes list filters with the FastAPI query parameter names", async () => {
    requestJsonMock.mockResolvedValue({ items: [transaction] });

    await expect(listTransactions(filters)).resolves.toEqual([transaction]);

    expect(requestJsonMock).toHaveBeenCalledWith(
      "/transactions?from=2026-08-01&to=2026-08-31&type=expense&category_id=category%2Fone&account_id=account+one",
    );
  });

  it("omits the question mark when no filters are active", async () => {
    requestJsonMock.mockResolvedValue({ items: [] });

    await listTransactions({ from: "", to: "", type: "", categoryId: "", accountId: "" });

    expect(requestJsonMock).toHaveBeenCalledWith("/transactions");
  });

  it("creates a transaction with the API field names", async () => {
    requestJsonMock.mockResolvedValue(transaction);

    await saveTransaction(undefined, payload);

    expect(requestJsonMock).toHaveBeenCalledWith("/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  });

  it("updates a transaction through its FastAPI resource URL", async () => {
    requestJsonMock.mockResolvedValue(transaction);

    await saveTransaction("transaction-1", payload);

    expect(requestJsonMock).toHaveBeenCalledWith("/transactions/transaction-1", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  });

  it("deletes a transaction through its FastAPI resource URL", async () => {
    requestJsonMock.mockResolvedValue(null);

    await deleteTransaction("transaction-1");

    expect(requestJsonMock).toHaveBeenCalledWith("/transactions/transaction-1", {
      method: "DELETE",
    });
  });

  it("retries categorization with POST on the transaction action URL", async () => {
    requestJsonMock.mockResolvedValue({
      ...transaction,
      category_id: null,
      category_source: null,
      categorization_status: "pending",
      categorized_at: null,
    });

    await retryCategorization("transaction-1");

    expect(requestJsonMock).toHaveBeenCalledWith(
      "/transactions/transaction-1/categorize",
      { method: "POST" },
    );
  });
});

describe("rule keyword suggestion", () => {
  it("normalizes description whitespace and casing", () => {
    expect(suggestRuleKeyword("  SPOTIFY\n\tPremium  ")).toBe("spotify premium");
  });

  it("limits a suggested keyword to 120 characters", () => {
    expect(suggestRuleKeyword("A".repeat(121))).toBe("a".repeat(120));
  });
});
