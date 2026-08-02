"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/cn";
import styles from "./app-shell-nav.module.css";

const navigationItems = [
  { href: "/", label: "Dashboard" },
  { href: "/transactions", label: "Transactions" },
  { href: "/categories", label: "Categories" },
  { href: "/accounts", label: "Accounts" },
  { href: "/rules", label: "Rules" },
];

interface AppShellNavProps {
  children: React.ReactNode;
}

export function AppShellNav({ children }: AppShellNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { configured, loading, session, signOut } = useAuth();

  async function handleAuthAction() {
    if (session) {
      await signOut();
      router.push("/login");
      return;
    }

    router.push("/login");
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brandGroup}>
          <div className={styles.brandMark} aria-hidden="true">
            F
          </div>
          <div>
            <p className={styles.brandLabel}>Finance Flow</p>
            <p className={styles.brandMeta}>Personal finance dashboard</p>
          </div>
        </div>

        <nav className={styles.nav} aria-label="Primary">
          {navigationItems.map((item) => {
            const active =
              item.href === "/"
                ? pathname === item.href
                : pathname.startsWith(item.href);

            return (
              <Link
                className={cn(styles.navLink, active && styles.active)}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className={styles.actions}>
          {session ? (
            <div className={styles.authGroup}>
              <span className={styles.authMeta}>
                {session.user.email ?? "Signed in"}
              </span>
              <Button onClick={handleAuthAction} size="sm" variant="secondary">
                <LogOut size={16} />
                Sign out
              </Button>
            </div>
          ) : (
            <Button
              disabled={loading && configured}
              onClick={handleAuthAction}
              size="sm"
              variant="secondary"
            >
              Sign in
            </Button>
          )}
          <Button onClick={() => router.push("/transactions")} size="sm">
            <Plus size={16} />
            New transaction
          </Button>
        </div>
      </header>

      <main className={styles.content}>{children}</main>
    </div>
  );
}
