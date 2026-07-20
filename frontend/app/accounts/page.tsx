import { AppShellNav } from "@/components/layout/app-shell-nav";
import { Card } from "@/components/ui/card";
import styles from "../page.module.css";

export default function AccountsPage() {
  return (
    <AppShellNav>
      <Card className={styles.card}>
        <p className={styles.eyebrow}>Accounts</p>
        <h1 className={styles.title}>Keep balances connected.</h1>
        <p className={styles.subtitle}>
          This section will hold checking, savings, and cash accounts.
        </p>
      </Card>
    </AppShellNav>
  );
}

