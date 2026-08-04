"use client";

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { DashboardResponse } from "@/lib/dashboard";
import styles from "./category-donut.module.css";

interface CategoryDonutProps {
  categories: DashboardResponse["categories"];
}

const currencyFormatter = new Intl.NumberFormat("sv-SE", {
  style: "currency",
  currency: "SEK",
});

function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

export function CategoryDonut({ categories }: CategoryDonutProps) {
  const chartData = categories.map((category) => ({
    ...category,
    amount: Number(category.amount),
    percentage: Number(category.percentage),
  }));

  return (
    <div className={styles.chart}>
      <div className={styles.visual} aria-hidden="true">
        <ResponsiveContainer height={260} width="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="amount"
              innerRadius="55%"
              nameKey="name"
              outerRadius="82%"
              paddingAngle={2}
            >
              {chartData.map((category) => (
                <Cell fill={category.color} key={category.category_id ?? category.name} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatCurrency(Number(value))} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul aria-label="Expense categories" className={styles.summary}>
        {categories.map((category) => (
          <li className={styles.summaryItem} key={category.category_id ?? category.name}>
            <span>{category.name}</span>
            <span>
              {formatCurrency(Number(category.amount))} ({category.percentage}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
