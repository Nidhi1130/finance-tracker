"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/auth-provider";
import { CashFlowChart } from "@/components/dashboard/cash-flow-chart";
import { CategoryDonut } from "@/components/dashboard/category-donut";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import {
  dashboardQueryKey,
  getDashboard,
  lastMonthPeriod,
  thisMonthPeriod,
} from "@/lib/dashboard";
import styles from "./page.module.css";

type SummaryTone = "income" | "expense";

const currencyFormatter = new Intl.NumberFormat("sv-SE", {
  style: "currency",
  currency: "SEK",
});

function formatCurrency(value: string): string {
  return currencyFormatter.format(Number(value));
}

interface SummaryCardProps {
  label: string;
  value: string;
  tone: SummaryTone;
}

function SummaryCard({ label, value, tone }: SummaryCardProps) {
  return (
    <Card className={cn(styles.summaryCard, styles[tone])}>
      <p className={styles.summaryLabel}>{label}</p>
      <p className={styles.summaryValue}>{value}</p>
    </Card>
  );
}

export function DashboardClient() {
  const router = useRouter();
  const { configured, loading: authLoading, session } = useAuth();
  const [period, setPeriod] = useState(() => thisMonthPeriod(new Date()));
  const [customOpen, setCustomOpen] = useState(false);
  const [draftPeriod, setDraftPeriod] = useState(period);
  const userId = session?.user.id ?? "development-user";
  const canApplyCustom = Boolean(
    draftPeriod.from && draftPeriod.to && draftPeriod.from <= draftPeriod.to,
  );

  const dashboardQuery = useQuery({
    queryKey: dashboardQueryKey(userId, period.from, period.to),
    queryFn: () => getDashboard(period.from, period.to),
    enabled: !configured || Boolean(session),
  });

  function applyPreset(nextPeriod: typeof period) {
    setPeriod(nextPeriod);
    setDraftPeriod(nextPeriod);
    setCustomOpen(false);
  }

  function openCustomPeriod() {
    setDraftPeriod(period);
    setCustomOpen(true);
  }

  function applyCustomPeriod() {
    if (canApplyCustom) {
      setPeriod(draftPeriod);
      setCustomOpen(false);
    }
  }

  if (authLoading) {
    return (
      <Card className={styles.stateCard}>
        <p className={styles.stateMessage}>Checking your session...</p>
      </Card>
    );
  }

  if (configured && !session) {
    return (
      <Card className={styles.stateCard}>
        <p className={styles.eyebrow}>Authentication required</p>
        <h1 className={styles.title}>Sign in to view your dashboard.</h1>
        <p className={styles.subtitle}>
          Sign in to see your income, expenses, and net balance for each period.
        </p>
        <div className={styles.actions}>
          <Button onClick={() => router.push("/login")}>Go to sign in</Button>
        </div>
      </Card>
    );
  }

  const data = dashboardQuery.data;
  const isEmpty = data?.categories.length === 0 && data.trend.length === 0;

  return (
    <section className={styles.dashboard} aria-labelledby="dashboard-title">
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Dashboard</p>
          <h1 className={styles.title} id="dashboard-title">
            See your money story at a glance.
          </h1>
          <p className={styles.subtitle}>
            Review income, expenses, and net balance for the period you choose.
          </p>
        </div>
        <div className={styles.periodControls} aria-label="Dashboard period">
          <Button
            onClick={() => applyPreset(thisMonthPeriod(new Date()))}
            size="sm"
            variant="secondary"
          >
            This month
          </Button>
          <Button
            onClick={() => applyPreset(lastMonthPeriod(new Date()))}
            size="sm"
            variant="secondary"
          >
            Last month
          </Button>
          <Button onClick={openCustomPeriod} size="sm" variant="secondary">
            Custom
          </Button>
        </div>
      </div>

      {customOpen ? (
        <div className={styles.customPeriod}>
          <Input
            aria-label="Custom from date"
            type="date"
            value={draftPeriod.from}
            onChange={(event) =>
              setDraftPeriod((current) => ({ ...current, from: event.target.value }))
            }
          />
          <Input
            aria-label="Custom to date"
            type="date"
            value={draftPeriod.to}
            onChange={(event) =>
              setDraftPeriod((current) => ({ ...current, to: event.target.value }))
            }
          />
          <Button disabled={!canApplyCustom} onClick={applyCustomPeriod} size="sm">
            Apply
          </Button>
        </div>
      ) : null}

      {dashboardQuery.isLoading && !data ? (
        <div className={styles.summaryGrid} aria-label="Loading dashboard">
          {["income", "expense", "net"].map((item) => (
            <div className={styles.skeleton} key={item} />
          ))}
        </div>
      ) : null}

      {dashboardQuery.isError ? (
        <Card className={styles.stateCard}>
          <p className={styles.error}>
            {dashboardQuery.error instanceof Error
              ? dashboardQuery.error.message
              : "Unable to load dashboard"}
          </p>
          <div className={styles.actions}>
            <Button onClick={() => void dashboardQuery.refetch()}>Retry</Button>
          </div>
        </Card>
      ) : null}

      {data ? (
        <>
          <div className={styles.summaryGrid}>
            <SummaryCard label="Income" value={formatCurrency(data.summary.income)} tone="income" />
            <SummaryCard label="Expense" value={formatCurrency(data.summary.expense)} tone="expense" />
            <SummaryCard
              label="Net"
              value={formatCurrency(data.summary.net)}
              tone={Number(data.summary.net) >= 0 ? "income" : "expense"}
            />
          </div>
          <div className={styles.chartGrid}>
            {data.categories.length > 0 ? (
              <Card aria-labelledby="expense-categories-title" className={styles.chartCard}>
                <h2 className={styles.chartTitle} id="expense-categories-title">
                  Expense categories
                </h2>
                <CategoryDonut categories={data.categories} />
              </Card>
            ) : (
              <p className={styles.empty}>No expense categories in this period</p>
            )}
            {data.trend.length > 0 ? (
              <Card aria-labelledby="cash-flow-title" className={styles.chartCard}>
                <h2 className={styles.chartTitle} id="cash-flow-title">
                  Cash flow
                </h2>
                <CashFlowChart points={data.trend} />
              </Card>
            ) : (
              <p className={styles.empty}>No cash-flow activity in this period</p>
            )}
          </div>
          {isEmpty ? <p className={styles.empty}>No transactions in this period</p> : null}
        </>
      ) : null}
    </section>
  );
}
