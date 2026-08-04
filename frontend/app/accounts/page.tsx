import { AppShellNav } from "@/components/layout/app-shell-nav";
import { ResourceManager } from "@/components/resources/resource-manager";

export default function AccountsPage() {
  return (
    <AppShellNav>
      <ResourceManager
        endpoint="/accounts"
        eyebrow="Accounts"
        singular="account"
        subtitle="Create private accounts for checking, savings, cash, or any other source you want to track."
        title="Keep every account connected."
      />
    </AppShellNav>
  );
}
