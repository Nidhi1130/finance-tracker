import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./app-shell.module.css";

interface AppShellProps extends HTMLAttributes<HTMLElement> {
  centered?: boolean;
  children: ReactNode;
}

export function AppShell({
  centered = false,
  className,
  children,
  ...props
}: AppShellProps) {
  return (
    <main
      className={cn(styles.shell, centered && styles.centered, className)}
      {...props}
    >
      {children}
    </main>
  );
}

