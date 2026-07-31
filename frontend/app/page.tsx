import { AppShellNav } from "@/components/layout/app-shell-nav";
import { DashboardClient } from "./dashboard-client";

export default function Home() {
  return (
    <AppShellNav>
      <DashboardClient />
    </AppShellNav>
  );
}
