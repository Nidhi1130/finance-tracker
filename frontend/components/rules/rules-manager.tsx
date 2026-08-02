"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import {
  categorizationRuleQueryKey,
  createCategorizationRule,
  deleteCategorizationRule,
  listCategorizationRules,
  updateCategorizationRule,
} from "@/lib/categorization-rules";
import { categoryQueryKey, listCategories } from "@/lib/categories";
import styles from "./rules-manager.module.css";

interface EditorState {
  ruleId: string | null;
  keyword: string;
  categoryId: string;
  enabled: boolean;
}

const initialEditor: EditorState = {
  ruleId: null,
  keyword: "",
  categoryId: "",
  enabled: true,
};

export function RulesManager() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { configured, loading: authLoading, session } = useAuth();
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [deleteRuleId, setDeleteRuleId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const userId = session?.user.id ?? "development-user";
  const enabled = !configured || Boolean(session);
  const ruleQueryKey = categorizationRuleQueryKey(userId);

  const rulesQuery = useQuery({
    queryKey: ruleQueryKey,
    enabled,
    queryFn: listCategorizationRules,
  });
  const categoriesQuery = useQuery({
    queryKey: categoryQueryKey(userId),
    enabled,
    queryFn: listCategories,
  });

  const saveMutation = useMutation({
    mutationFn: (nextEditor: EditorState) => {
      const payload = {
        keyword: nextEditor.keyword.trim(),
        category_id: nextEditor.categoryId,
        enabled: nextEditor.enabled,
      };
      return nextEditor.ruleId
        ? updateCategorizationRule(nextEditor.ruleId, payload)
        : createCategorizationRule(payload);
    },
    onSuccess: async () => {
      setEditor(null);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ruleQueryKey, exact: true });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, nextEnabled }: { ruleId: string; nextEnabled: boolean }) =>
      updateCategorizationRule(ruleId, { enabled: nextEnabled }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ruleQueryKey, exact: true });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCategorizationRule,
    onSuccess: async () => {
      setDeleteRuleId(null);
      await queryClient.invalidateQueries({ queryKey: ruleQueryKey, exact: true });
    },
  });

  function openCreate() {
    saveMutation.reset();
    setFormError(null);
    setEditor(initialEditor);
  }

  function openEdit(rule: { id: string; keyword: string; category_id: string; enabled: boolean }) {
    saveMutation.reset();
    setFormError(null);
    setEditor({
      ruleId: rule.id,
      keyword: rule.keyword,
      categoryId: rule.category_id,
      enabled: rule.enabled,
    });
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor) return;
    if (!editor.keyword.trim() || !editor.categoryId) {
      setFormError("Enter a keyword and select a category.");
      return;
    }

    setFormError(null);
    try {
      await saveMutation.mutateAsync(editor);
    } catch {
      // The mutation error is displayed in the dialog.
    }
  }

  async function handleToggle(ruleId: string, nextEnabled: boolean) {
    try {
      await toggleMutation.mutateAsync({ ruleId, nextEnabled });
    } catch {
      // The mutation error is displayed above the list.
    }
  }

  async function handleDelete() {
    if (!deleteRuleId) return;
    try {
      await deleteMutation.mutateAsync(deleteRuleId);
    } catch {
      // The mutation error is displayed in the confirmation dialog.
    }
  }

  if (authLoading) {
    return <Card><p className={styles.status}>Checking your session...</p></Card>;
  }

  if (configured && !session) {
    return (
      <Card className={styles.panel}>
        <p className={styles.eyebrow}>Authentication required</p>
        <h1 className={styles.title}>Sign in to manage categorization rules.</h1>
        <Button onClick={() => router.push("/login")}>Go to sign in</Button>
      </Card>
    );
  }

  const rules = rulesQuery.data ?? [];
  const categories = categoriesQuery.data ?? [];
  const error =
    rulesQuery.error instanceof Error
      ? rulesQuery.error.message
      : categoriesQuery.error instanceof Error
        ? categoriesQuery.error.message
        : toggleMutation.error instanceof Error
          ? toggleMutation.error.message
          : null;

  return (
    <Card className={styles.panel}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Smart categorization</p>
          <h1 className={styles.title}>Rules that recognize your spending.</h1>
          <p className={styles.subtitle}>
            Match transaction descriptions to a category before automatic categorization runs.
          </p>
        </div>
        <Button onClick={openCreate}>New rule</Button>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {rulesQuery.isLoading ? <p className={styles.status}>Loading categorization rules...</p> : null}
      {!rulesQuery.isLoading && rules.length === 0 ? (
        <p className={styles.status}>No categorization rules yet.</p>
      ) : null}

      <div className={styles.list}>
        {rules.map((rule) => (
          <div className={styles.row} key={rule.id}>
            <div className={styles.identity}>
              <span
                aria-hidden="true"
                className={styles.swatch}
                style={{ background: rule.category_color }}
              />
              <div>
                <p className={styles.keyword}>{rule.keyword}</p>
                <p className={styles.meta}>{rule.category_name}</p>
              </div>
            </div>
            <div className={styles.actions}>
              <span className={rule.enabled ? styles.enabled : styles.disabled}>
                {rule.enabled ? "Enabled" : "Disabled"}
              </span>
              <Button
                aria-label={`${rule.enabled ? "Disable" : "Enable"} ${rule.keyword}`}
                disabled={toggleMutation.isPending}
                onClick={() => void handleToggle(rule.id, !rule.enabled)}
                size="sm"
                variant="secondary"
              >
                {rule.enabled ? "Disable" : "Enable"}
              </Button>
              <Button aria-label={`Edit ${rule.keyword}`} onClick={() => openEdit(rule)} size="sm" variant="secondary">
                Edit
              </Button>
              <Button aria-label={`Delete ${rule.keyword}`} onClick={() => setDeleteRuleId(rule.id)} size="sm" variant="ghost">
                Delete
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Modal
        description="Choose a keyword, category, and whether this rule should apply automatically."
        onClose={() => setEditor(null)}
        open={editor !== null}
        title={editor?.ruleId ? "Edit rule" : "Create rule"}
      >
        {editor ? (
          <form className={styles.form} onSubmit={handleSave}>
            <label className={styles.label}>
              Keyword
              <Input
                autoFocus
                maxLength={120}
                value={editor.keyword}
                onChange={(event) => setEditor({ ...editor, keyword: event.target.value })}
              />
            </label>
            <label className={styles.label}>
              Category
              <Select
                value={editor.categoryId}
                onChange={(event) => setEditor({ ...editor, categoryId: event.target.value })}
              >
                <option value="">Select a category</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </Select>
            </label>
            <label className={styles.checkbox}>
              <input
                checked={editor.enabled}
                type="checkbox"
                onChange={(event) => setEditor({ ...editor, enabled: event.target.checked })}
              />
              Enabled
            </label>
            {formError ? <p className={styles.error}>{formError}</p> : null}
            {saveMutation.error instanceof Error ? <p className={styles.error}>{saveMutation.error.message}</p> : null}
            <div className={styles.actions}>
              <Button disabled={saveMutation.isPending} type="submit">
                {saveMutation.isPending ? "Saving..." : "Save rule"}
              </Button>
              <Button onClick={() => setEditor(null)} variant="secondary">Cancel</Button>
            </div>
          </form>
        ) : null}
      </Modal>

      <Modal
        description="Transactions will no longer be matched by this keyword."
        onClose={() => setDeleteRuleId(null)}
        open={deleteRuleId !== null}
        title="Delete this rule?"
      >
        {deleteMutation.error instanceof Error ? <p className={styles.error}>{deleteMutation.error.message}</p> : null}
        <div className={styles.actions}>
          <Button disabled={deleteMutation.isPending} onClick={() => void handleDelete()}>
            {deleteMutation.isPending ? "Deleting..." : "Delete rule"}
          </Button>
          <Button onClick={() => setDeleteRuleId(null)} variant="secondary">Cancel</Button>
        </div>
      </Modal>
    </Card>
  );
}
