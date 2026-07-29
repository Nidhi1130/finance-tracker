"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { requestJson } from "@/lib/api";
import { accountQueryKey, listAccounts } from "@/lib/accounts";
import { categoryQueryKey, listCategories } from "@/lib/categories";
import { cn } from "@/lib/cn";
import { useAuth } from "@/components/auth/auth-provider";
import styles from "./transactions.module.css";

type TxType = "income" | "expense";

interface Transaction {
  id: string;
  amount: string;
  type: TxType;
  description: string | null;
  date: string;
  category_id: string | null;
  account_id: string | null;
  created_at: string;
  updated_at: string;
}

interface TransactionListResponse {
  items: Transaction[];
}

interface TransactionFormState {
  amount: string;
  type: TxType;
  date: string;
  description: string;
  categoryId: string;
  accountId: string;
}

interface TransactionFilters {
  from: string;
  to: string;
  type: "" | TxType;
  categoryId: string;
  accountId: string;
}

interface TransactionPayload {
  amount: string;
  type: TxType;
  date: string;
  description: string | null;
  category_id: string | null;
  account_id: string | null;
}

const today = new Date().toISOString().slice(0, 10);

const initialFormState: TransactionFormState = {
  amount: "",
  type: "expense",
  date: today,
  description: "",
  categoryId: "",
  accountId: "",
};

const initialFilters: TransactionFilters = {
  from: "",
  to: "",
  type: "",
  categoryId: "",
  accountId: "",
};

function buildQueryString(filters: TransactionFilters): string {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.type) params.set("type", filters.type);
  if (filters.categoryId) params.set("category_id", filters.categoryId);
  if (filters.accountId) params.set("account_id", filters.accountId);
  return params.toString();
}

function normalizeNullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function toPayload(form: TransactionFormState): TransactionPayload {
  return {
    amount: form.amount,
    type: form.type,
    date: form.date,
    description: normalizeNullable(form.description),
    category_id: normalizeNullable(form.categoryId),
    account_id: normalizeNullable(form.accountId),
  };
}

export function TransactionsClient() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { configured, loading: authLoading, session } = useAuth();
  const [form, setForm] = useState<TransactionFormState>(initialFormState);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [filters, setFilters] = useState<TransactionFilters>(initialFilters);
  const userId = session?.user.id ?? "development-user";
  const enabled = !configured || Boolean(session);

  const transactionsQuery = useQuery({
    queryKey: ["transactions", userId, filters],
    enabled,
    queryFn: async () => {
      const queryString = buildQueryString(filters);
      const response = await requestJson<TransactionListResponse>(
        `/transactions${queryString ? `?${queryString}` : ""}`,
      );
      return response.items;
    },
  });

  const categoriesQuery = useQuery({
    queryKey: categoryQueryKey(userId),
    enabled,
    queryFn: listCategories,
  });

  const accountsQuery = useQuery({
    queryKey: accountQueryKey(userId),
    enabled,
    queryFn: listAccounts,
  });

  const saveMutation = useMutation({
    mutationFn: async ({
      transactionId,
      payload,
    }: {
      transactionId?: string;
      payload: TransactionPayload;
    }) => {
      const path = transactionId ? `/transactions/${transactionId}` : "/transactions";
      const method = transactionId ? "PUT" : "POST";
      return requestJson<Transaction>(path, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    },
    onSuccess: async () => {
      setForm(initialFormState);
      setEditingTransaction(null);
      await queryClient.invalidateQueries({ queryKey: ["transactions", userId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (transactionId: string) => {
      await requestJson<null>(`/transactions/${transactionId}`, {
        method: "DELETE",
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["transactions", userId] });
    },
  });

  const items = transactionsQuery.data ?? [];
  const categories = useMemo(
    () => categoriesQuery.data ?? [],
    [categoriesQuery.data],
  );
  const accounts = useMemo(
    () => accountsQuery.data ?? [],
    [accountsQuery.data],
  );
  const loading = transactionsQuery.isLoading;
  const requestErrorMessage =
    transactionsQuery.error instanceof Error
      ? transactionsQuery.error.message
      : saveMutation.error instanceof Error
        ? saveMutation.error.message
        : deleteMutation.error instanceof Error
          ? deleteMutation.error.message
          : null;
  const resourceErrorMessage =
    categoriesQuery.error instanceof Error
      ? categoriesQuery.error.message
      : accountsQuery.error instanceof Error
        ? accountsQuery.error.message
        : null;
  const errorMessage = requestErrorMessage ?? resourceErrorMessage;
  const isSaving = saveMutation.isPending;
  const isDeleting = deleteMutation.isPending;
  const isEditing = editingTransaction !== null;
  const referencesLoading = categoriesQuery.isLoading || accountsQuery.isLoading;
  const categoryNames = useMemo(
    () => new Map(categories.map((category) => [category.id, category.name])),
    [categories],
  );
  const accountNames = useMemo(
    () => new Map(accounts.map((account) => [account.id, account.name])),
    [accounts],
  );

  async function handleSignInRedirect() {
    router.push("/login");
  }

  function updateForm<K extends keyof TransactionFormState>(
    key: K,
    value: TransactionFormState[K],
  ) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function resetForm() {
    setForm(initialFormState);
    setEditingTransaction(null);
  }

  function clearFilters() {
    setFilters(initialFilters);
  }

  function startEdit(transaction: Transaction) {
    setEditingTransaction(transaction);
    setForm({
      amount: transaction.amount,
      type: transaction.type,
      date: transaction.date,
      description: transaction.description ?? "",
      categoryId: transaction.category_id ?? "",
      accountId: transaction.account_id ?? "",
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await saveMutation.mutateAsync({
        transactionId: editingTransaction?.id,
        payload: toPayload(form),
      });
    } catch {
      // Mutation state already feeds the error banner.
    }
  }

  async function handleDelete(transactionId: string) {
    try {
      await deleteMutation.mutateAsync(transactionId);
      if (editingTransaction?.id === transactionId) {
        resetForm();
      }
    } catch {
      // Mutation state already feeds the error banner.
    }
  }

  const emptyState = useMemo(() => {
    if (loading) {
      return "Loading transactions...";
    }

    if (items.length === 0) {
      return "No transactions yet.";
    }

    return null;
  }, [items.length, loading]);

  return (
    <div className={styles.grid}>
      {authLoading ? (
        <Card className={styles.panel}>
          <p className={styles.empty}>Checking your session...</p>
        </Card>
      ) : null}

      {!authLoading && configured && !session ? (
        <Card className={styles.panel}>
          <p className={styles.eyebrow}>Authentication required</p>
          <h1 className={styles.title}>Sign in to view transactions.</h1>
          <p className={styles.subtitle}>
            This page now uses a real Supabase session. Sign in first, then
            you can add and manage transactions.
          </p>
          <div className={styles.formActions}>
            <Button onClick={handleSignInRedirect} type="button">
              Go to sign in
            </Button>
          </div>
        </Card>
      ) : null}

      {(!configured || session) && !authLoading ? (
        <>
          <Card className={styles.panel}>
            <div className={styles.header}>
              <div>
                <p className={styles.eyebrow}>Transactions</p>
                <h1 className={styles.title}>Track every money move in one place.</h1>
                <p className={styles.subtitle}>
                  Create, edit, filter, and delete income or expense transactions with
                  category and optional account references.
                </p>
              </div>
              <Button onClick={resetForm} type="button">
                New transaction
              </Button>
            </div>

            <div className={styles.filters}>
              <Input
                aria-label="Filter from date"
                type="date"
                value={filters.from}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, from: event.target.value }))
                }
              />
              <Input
                aria-label="Filter to date"
                type="date"
                value={filters.to}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, to: event.target.value }))
                }
              />
              <select
                className={styles.select}
                value={filters.type}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    type: event.target.value as TransactionFilters["type"],
                  }))
                }
              >
                <option value="">All types</option>
                <option value="income">Income</option>
                <option value="expense">Expense</option>
              </select>
              <select
                aria-label="Filter by category"
                className={styles.select}
                value={filters.categoryId}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, categoryId: event.target.value }))
                }
              >
                <option value="">All categories</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <select
                aria-label="Filter by account"
                className={styles.select}
                value={filters.accountId}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, accountId: event.target.value }))
                }
              >
                <option value="">All accounts</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
              <Button onClick={clearFilters} type="button" variant="secondary">
                Clear filters
              </Button>
            </div>

            {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
            {emptyState ? <p className={styles.empty}>{emptyState}</p> : null}

            {!loading && items.length > 0 ? (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Category</th>
                      <th>Account</th>
                      <th>Type</th>
                      <th className={styles.amountCol}>Amount</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => {
                      const categoryLabel = item.category_id
                        ? categoryNames.get(item.category_id) ?? "Unavailable category"
                        : "Uncategorized";
                      const accountLabel = item.account_id
                        ? accountNames.get(item.account_id) ?? "Unavailable account"
                        : "No account";

                      return (
                        <tr key={item.id}>
                          <td>{item.date}</td>
                          <td>{item.description ?? "—"}</td>
                          <td>{categoryLabel}</td>
                          <td>{accountLabel}</td>
                          <td>
                            <span
                              className={cn(
                                styles.pill,
                                item.type === "income" ? styles.income : styles.expense,
                              )}
                            >
                              {item.type}
                            </span>
                          </td>
                          <td className={styles.amountCol}>{item.amount}</td>
                          <td>
                            <div className={styles.rowActions}>
                              <Button
                                onClick={() => startEdit(item)}
                                size="sm"
                                type="button"
                                variant="secondary"
                              >
                                Edit
                              </Button>
                              <Button
                                disabled={isDeleting}
                                onClick={() => void handleDelete(item.id)}
                                size="sm"
                                type="button"
                                variant="ghost"
                              >
                                Delete
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </Card>

          <Card className={styles.panel}>
            <div className={styles.formHeader}>
              <div>
                <p className={styles.eyebrow}>{isEditing ? "Edit transaction" : "New transaction"}</p>
                <h2 className={styles.sectionTitle}>
                  {isEditing ? "Update the existing transaction" : "Create a new transaction"}
                </h2>
              </div>
              {isEditing ? (
                <Button onClick={resetForm} type="button" variant="secondary">
                  Cancel edit
                </Button>
              ) : null}
            </div>

            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.formGrid}>
                <Input
                  placeholder="Amount"
                  step="0.01"
                  min="0.01"
                  required
                  type="number"
                  value={form.amount}
                  onChange={(event) => updateForm("amount", event.target.value)}
                />
                <select
                  className={styles.select}
                  value={form.type}
                  onChange={(event) => updateForm("type", event.target.value as TxType)}
                >
                  <option value="expense">Expense</option>
                  <option value="income">Income</option>
                </select>
                <Input
                  required
                  type="date"
                  value={form.date}
                  onChange={(event) => updateForm("date", event.target.value)}
                />
                <select
                  aria-label="Category"
                  className={styles.select}
                  value={form.categoryId}
                  onChange={(event) => updateForm("categoryId", event.target.value)}
                >
                  <option value="">Uncategorized</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Account"
                  className={styles.select}
                  value={form.accountId}
                  onChange={(event) => updateForm("accountId", event.target.value)}
                >
                  <option value="">No account</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </div>

              <Textarea
                placeholder="Description"
                value={form.description}
                onChange={(event) => updateForm("description", event.target.value)}
              />

              <p className={styles.helper}>
                Amount stays positive. The `type` field controls whether it is income or expense.
              </p>

              <div className={styles.formActions}>
                <Button disabled={isSaving || referencesLoading} type="submit">
                  {isSaving
                    ? "Saving..."
                    : referencesLoading
                      ? "Loading categories and accounts..."
                    : isEditing
                      ? "Update transaction"
                      : "Create transaction"}
                </Button>
              </div>
            </form>
          </Card>
        </>
      ) : null}
    </div>
  );
}
