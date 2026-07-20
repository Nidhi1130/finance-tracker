"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/components/auth/auth-provider";
import styles from "./login.module.css";

export function LoginClient() {
  const router = useRouter();
  const { signInWithPassword, loading, configured, session } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (session) {
      router.push("/transactions");
    }
  }, [router, session]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    try {
      await signInWithPassword(email, password);
      router.push("/transactions");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Sign in failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className={styles.status}>Checking your session...</p>;
  }

  if (!configured) {
    return (
      <Card className={styles.card}>
        <p className={styles.eyebrow}>Supabase not configured</p>
        <h1 className={styles.title}>Set up `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.</h1>
        <p className={styles.subtitle}>
          The login form needs a real Supabase project to work. Add the
          values to your local environment and restart the frontend.
        </p>
      </Card>
    );
  }

  if (session) {
    return <p className={styles.status}>Redirecting to transactions...</p>;
  }

  return (
    <div className={styles.page}>
      <Card className={styles.card}>
        <p className={styles.eyebrow}>Finance Flow</p>
        <h1 className={styles.title}>Sign in to Finance Flow</h1>
        <p className={styles.subtitle}>
          Use your Supabase email and password to access transactions,
          categories, and accounts.
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <Input
            autoComplete="email"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Input
            autoComplete="current-password"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error ? <p className={styles.error}>{error}</p> : null}
          <Button disabled={saving} type="submit">
            {saving ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
