import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./scroll-area.module.css";

interface ScrollAreaProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function ScrollArea({
  className,
  children,
  ...props
}: ScrollAreaProps) {
  return (
    <div className={cn(styles.scrollArea, className)} {...props}>
      {children}
    </div>
  );
}

