"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/components/auth/auth-provider";
import styles from "./signup.module.css";

export function SignupClient() {
  const router = useRouter();
  const { signUp, loading, configured, session } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [checkEmail, setCheckEmail] = useState(false);

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
      const { requiresEmailConfirmation } = await signUp(email, password);
      if (requiresEmailConfirmation) {
        setCheckEmail(true);
      } else {
        router.push("/transactions");
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Sign up failed");
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
          Sign-up needs a real Supabase project to work. Add the values to
          your local environment and restart the frontend.
        </p>
      </Card>
    );
  }

  if (session) {
    return <p className={styles.status}>Redirecting to transactions...</p>;
  }

  if (checkEmail) {
    return (
      <div className={styles.page}>
        <Card className={styles.card}>
          <p className={styles.eyebrow}>Finance Flow</p>
          <h1 className={styles.title}>Check your email</h1>
          <p className={styles.subtitle}>
            We sent a confirmation link to {email}. Click it and you&apos;ll
            be brought straight back into the app, signed in. If nothing
            happens,{" "}
            <Link className={styles.link} href="/login">
              sign in manually
            </Link>
            .
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Card className={styles.card}>
        <p className={styles.eyebrow}>Finance Flow</p>
        <h1 className={styles.title}>Create your account</h1>
        <p className={styles.subtitle}>
          Sign up with an email and password to start tracking transactions,
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
            autoComplete="new-password"
            minLength={6}
            placeholder="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error ? <p className={styles.error}>{error}</p> : null}
          <Button disabled={saving} type="submit">
            {saving ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <p className={styles.footer}>
          Already have an account?{" "}
          <Link className={styles.link} href="/login">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
