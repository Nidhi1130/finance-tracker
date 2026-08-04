"use client";

import type { SelectHTMLAttributes } from "react";
import { forwardRef } from "react";
import { cn } from "@/lib/cn";
import styles from "./select.module.css";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, ...props },
  ref,
) {
  return <select ref={ref} className={cn(styles.select, className)} {...props} />;
});
