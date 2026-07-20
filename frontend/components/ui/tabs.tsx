"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./tabs.module.css";

export interface TabItem {
  label: string;
  value: string;
}

interface TabsProps {
  items: TabItem[];
  value: string;
  onValueChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
  children?: ReactNode;
}

export function Tabs({
  items,
  value,
  onValueChange,
  ariaLabel = "Tabs",
  className,
  children,
}: TabsProps) {
  return (
    <div className={cn(styles.tabs, className)}>
      <div aria-label={ariaLabel} className={styles.list} role="tablist">
        {items.map((item) => {
          const active = item.value === value;

          return (
            <button
              aria-selected={active}
              className={cn(styles.tab, active && styles.active)}
              key={item.value}
              onClick={() => onValueChange(item.value)}
              role="tab"
              type="button"
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {children ? <div className={styles.content}>{children}</div> : null}
    </div>
  );
}

