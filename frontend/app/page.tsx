import { AppShellNav } from "@/components/layout/app-shell-nav";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import styles from "./page.module.css";

export default function Home() {
  return (
    <AppShellNav>
      <Card className={styles.card}>
        <p className={styles.eyebrow}>Finance Flow</p>
        <h1 className={styles.title}>Track money with clarity.</h1>
        <p className={styles.subtitle}>
          A focused workspace for transaction entry, category tagging, and
          the accounting flow that follows.
        </p>
        <div className={styles.actions}>
          <Button>Open dashboard</Button>
          <Button variant="secondary">View transactions</Button>
        </div>
      </Card>
    </AppShellNav>
  );
}
