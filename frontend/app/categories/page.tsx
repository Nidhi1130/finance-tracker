import { AppShellNav } from "@/components/layout/app-shell-nav";
import { ResourceManager } from "@/components/resources/resource-manager";

export default function CategoriesPage() {
  return (
    <AppShellNav>
      <ResourceManager
        endpoint="/categories"
        eyebrow="Categories"
        singular="category"
        subtitle="Use the global defaults or add your own labels. Your custom categories stay private to your account."
        title="Organize every money move."
        withColor
      />
    </AppShellNav>
  );
}
