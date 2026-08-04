"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardResponse } from "@/lib/dashboard";
import styles from "./cash-flow-chart.module.css";

interface CashFlowChartProps {
  points: DashboardResponse["trend"];
}

const currencyFormatter = new Intl.NumberFormat("sv-SE", {
  style: "currency",
  currency: "SEK",
});

function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

export function CashFlowChart({ points }: CashFlowChartProps) {
  const chartData = points.map((point) => ({
    ...point,
    income: Number(point.income),
    expense: Number(point.expense),
  }));

  return (
    <div className={styles.chart}>
      <div className={styles.visual} aria-hidden="true">
        <ResponsiveContainer height={300} width="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis tickFormatter={(value) => formatCurrency(Number(value))} />
            <Tooltip formatter={(value) => formatCurrency(Number(value))} />
            <Legend />
            <Bar dataKey="income" fill="var(--state-success)" name="Income" />
            <Bar dataKey="expense" fill="var(--state-error)" name="Expense" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table aria-label="Cash flow data" className={styles.visuallyHidden}>
        <thead>
          <tr>
            <th scope="col">Period</th>
            <th scope="col">Income</th>
            <th scope="col">Expense</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.period_start}>
              <th scope="row">{point.label}</th>
              <td>{formatCurrency(Number(point.income))}</td>
              <td>{formatCurrency(Number(point.expense))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
