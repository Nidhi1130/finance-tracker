import { requestJson } from "./api";

export type TxType = "income" | "expense";
export type CategorizationSource = "manual" | "rule" | "openai" | null;
export type CategorizationStatus =
  | "not_requested"
  | "pending"
  | "categorized"
  | "failed";

export interface Transaction {
  id: string;
  amount: string;
  type: TxType;
  description: string | null;
  date: string;
  category_id: string | null;
  account_id: string | null;
  category_source: CategorizationSource;
  categorization_status: CategorizationStatus;
  categorized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionFilters {
  from: string;
  to: string;
  type: "" | TxType;
  categoryId: string;
  accountId: string;
}

export interface TransactionPayload {
  amount: string;
  type: TxType;
  date: string;
  description: string | null;
  category_id: string | null;
  account_id: string | null;
}

interface TransactionListResponse {
  items: Transaction[];
}

export function transactionQueryKey(userId: string, filters: TransactionFilters) {
  return ["transactions", userId, filters] as const;
}

export async function listTransactions(filters: TransactionFilters): Promise<Transaction[]> {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.type) params.set("type", filters.type);
  if (filters.categoryId) params.set("category_id", filters.categoryId);
  if (filters.accountId) params.set("account_id", filters.accountId);
  const queryString = params.toString();

  return (
    await requestJson<TransactionListResponse>(
      `/transactions${queryString ? `?${queryString}` : ""}`,
    )
  ).items;
}

export async function saveTransaction(
  transactionId: string | undefined,
  payload: TransactionPayload,
): Promise<Transaction> {
  return requestJson<Transaction>(
    transactionId ? `/transactions/${transactionId}` : "/transactions",
    {
      method: transactionId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteTransaction(transactionId: string): Promise<void> {
  await requestJson<null>(`/transactions/${transactionId}`, { method: "DELETE" });
}

export async function retryCategorization(transactionId: string): Promise<Transaction> {
  return requestJson<Transaction>(`/transactions/${transactionId}/categorize`, {
    method: "POST",
  });
}

export function suggestRuleKeyword(description: string): string {
  return description.trim().replace(/\s+/g, " ").toLocaleLowerCase().slice(0, 120);
}
