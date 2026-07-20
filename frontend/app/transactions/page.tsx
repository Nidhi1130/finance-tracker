import { AppShellNav } from "@/components/layout/app-shell-nav";
import { TransactionsClient } from "./transactions-client";

export default function TransactionsPage() {
  return (
    <AppShellNav>
      <TransactionsClient />
    </AppShellNav>
  );
}
