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
import { requestJson } from "@/lib/api";
import styles from "./resource-manager.module.css";

interface ResourceItem {
  id: string;
  name: string;
  color?: string;
  is_global?: boolean;
  created_at: string;
}

interface ListResponse {
  items: ResourceItem[];
}

interface ResourceManagerProps {
  endpoint: "/categories" | "/accounts";
  eyebrow: string;
  title: string;
  subtitle: string;
  singular: "category" | "account";
  withColor?: boolean;
}

interface EditorState {
  item: ResourceItem | null;
  name: string;
  color: string;
}

const initialEditor: EditorState = { item: null, name: "", color: "#2563EB" };

const automaticCategoryColors = [
  "#7C3AED",
  "#16A34A",
  "#EA580C",
  "#2563EB",
  "#0891B2",
  "#DC2626",
  "#DB2777",
  "#CA8A04",
  "#059669",
  "#6B7280",
];

function automaticColorForName(name: string): string {
  const hash = [...name.trim().toLocaleLowerCase()].reduce(
    (total, character) => (total * 31 + character.charCodeAt(0)) >>> 0,
    0,
  );
  return automaticCategoryColors[hash % automaticCategoryColors.length];
}

export function ResourceManager({
  endpoint,
  eyebrow,
  title,
  subtitle,
  singular,
  withColor = false,
}: ResourceManagerProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { configured, loading: authLoading, session } = useAuth();
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ResourceItem | null>(null);
  const enabled = !configured || Boolean(session);

  const listQuery = useQuery({
    queryKey: [endpoint.slice(1)],
    enabled,
    queryFn: async () => (await requestJson<ListResponse>(endpoint)).items,
  });

  const saveMutation = useMutation({
    mutationFn: async (state: EditorState) =>
      requestJson<ResourceItem>(state.item ? `${endpoint}/${state.item.id}` : endpoint, {
        method: state.item ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          withColor
            ? {
                name: state.name,
                color: state.item ? state.color : automaticColorForName(state.name),
              }
            : { name: state.name },
        ),
      }),
    onSuccess: async () => {
      setEditor(null);
      await queryClient.invalidateQueries({ queryKey: [endpoint.slice(1)] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (item: ResourceItem) =>
      requestJson<null>(`${endpoint}/${item.id}`, { method: "DELETE" }),
    onSuccess: async () => {
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: [endpoint.slice(1)] });
      await queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  function openCreate() {
    saveMutation.reset();
    setEditor(initialEditor);
  }

  function openEdit(item: ResourceItem) {
    saveMutation.reset();
    setEditor({ item, name: item.name, color: item.color ?? initialEditor.color });
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor) return;
    try {
      await saveMutation.mutateAsync(editor);
    } catch {
      // The mutation error is rendered in the dialog.
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget);
    } catch {
      // The mutation error is rendered in the dialog.
    }
  }

  if (authLoading) {
    return <Card><p className={styles.status}>Checking your session...</p></Card>;
  }

  if (configured && !session) {
    return (
      <Card className={styles.panel}>
        <p className={styles.eyebrow}>Authentication required</p>
        <h1 className={styles.title}>Sign in to manage {endpoint.slice(1)}.</h1>
        <Button onClick={() => router.push("/login")}>Go to sign in</Button>
      </Card>
    );
  }

  const items = listQuery.data ?? [];
  const listError = listQuery.error instanceof Error ? listQuery.error.message : null;

  return (
    <Card className={styles.panel}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>{eyebrow}</p>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>{subtitle}</p>
        </div>
        <Button onClick={openCreate}>New {singular}</Button>
      </div>

      {listError ? <p className={styles.error}>{listError}</p> : null}
      {listQuery.isLoading ? <p className={styles.status}>Loading {endpoint.slice(1)}...</p> : null}
      {!listQuery.isLoading && items.length === 0 ? (
        <p className={styles.status}>No {endpoint.slice(1)} yet.</p>
      ) : null}

      <div className={styles.list}>
        {items.map((item) => (
          <div className={styles.row} key={item.id}>
            <div className={styles.identity}>
              {item.color ? (
                <span aria-hidden="true" className={styles.swatch} style={{ background: item.color }} />
              ) : null}
              <div>
                <p className={styles.name}>{item.name}</p>
                <p className={styles.meta}>
                  {item.is_global ? "Global default" : `Created ${new Date(item.created_at).toLocaleDateString()}`}
                </p>
              </div>
            </div>
            {item.is_global ? (
              <span className={styles.badge}>Read only</span>
            ) : (
              <div className={styles.actions}>
                <Button onClick={() => openEdit(item)} size="sm" variant="secondary">Edit</Button>
                <Button onClick={() => setDeleteTarget(item)} size="sm" variant="ghost">Delete</Button>
              </div>
            )}
          </div>
        ))}
      </div>

      <Modal
        description={`Names must be between 1 and 80 characters${withColor ? ". A color is assigned automatically" : ""}.`}
        onClose={() => setEditor(null)}
        open={editor !== null}
        title={`${editor?.item ? "Edit" : "Create"} ${singular}`}
      >
        {editor ? (
          <form className={styles.form} onSubmit={handleSave}>
            <label className={styles.label}>
              Name
              <Input
                autoFocus
                maxLength={80}
                required
                value={editor.name}
                onChange={(event) => setEditor({ ...editor, name: event.target.value })}
              />
            </label>
            {saveMutation.error instanceof Error ? <p className={styles.error}>{saveMutation.error.message}</p> : null}
            <div className={styles.actions}>
              <Button disabled={saveMutation.isPending} type="submit">
                {saveMutation.isPending ? "Saving..." : `Save ${singular}`}
              </Button>
              <Button onClick={() => setEditor(null)} variant="secondary">Cancel</Button>
            </div>
          </form>
        ) : null}
      </Modal>

      <Modal
        description={`Transactions using this ${singular} will be preserved and their reference cleared.`}
        onClose={() => setDeleteTarget(null)}
        open={deleteTarget !== null}
        title={`Delete ${deleteTarget?.name ?? singular}?`}
      >
        {deleteMutation.error instanceof Error ? <p className={styles.error}>{deleteMutation.error.message}</p> : null}
        <div className={styles.actions}>
          <Button disabled={deleteMutation.isPending} onClick={() => void handleDelete()}>
            {deleteMutation.isPending ? "Deleting..." : "Delete"}
          </Button>
          <Button onClick={() => setDeleteTarget(null)} variant="secondary">Cancel</Button>
        </div>
      </Modal>
    </Card>
  );
}
