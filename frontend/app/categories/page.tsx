import { AppShellNav } from "@/components/layout/app-shell-nav";
import { Card } from "@/components/ui/card";
import styles from "../page.module.css";

export default function CategoriesPage() {
  return (
    <AppShellNav>
      <Card className={styles.card}>
        <p className={styles.eyebrow}>Categories</p>
        <h1 className={styles.title}>Organize spending by category.</h1>
        <p className={styles.subtitle}>
          This section will manage the user categories that power the finance
          dashboard.
        </p>
      </Card>
    </AppShellNav>
  );
}

