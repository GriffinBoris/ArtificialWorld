<template>
  <AppShellFrame>
    <template #sidebar="{ isSidebarCollapsed, closeSidebar }">
      <SidebarNav
        :sections="navSections"
        :active-key="activeKey"
        :collapsed="isSidebarCollapsed"
        @select="(item) => handleSelect(item, closeSidebar)"
      >
        <template #header>
          <div class="flex items-center gap-1.5 px-1">
            <span class="text-body text-sm font-bold tracking-wider uppercase">{{ applicationStore.appName }}</span>
          </div>
        </template>

        <template #footer>
          <div
            class="flex items-center gap-2 px-1 py-1.5"
            :class="isSidebarCollapsed ? 'flex-col' : 'justify-between'"
          >
            <ThemeToggleButton
              :show-label="!isSidebarCollapsed"
              :root-class="isSidebarCollapsed ? undefined : 'flex-1 justify-start'"
            />
            <AppIconButton
              v-if="!authStore.localWorldAccess"
              icon="logout"
              label="Log out"
              tone="ghost"
              @click="handleLogout"
            />
          </div>
        </template>
      </SidebarNav>
    </template>

    <MainContentPane content-class="mx-auto flex min-h-full w-full max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <slot />
    </MainContentPane>
  </AppShellFrame>
</template>

<script setup lang="ts">
  import AppShellFrame from "@/components/layout/AppShellFrame.vue";
  import MainContentPane from "@/components/layout/MainContentPane.vue";
  import SidebarNav, { type SidebarNavItem, type SidebarNavSection } from "@/components/navigation/SidebarNav.vue";
  import AppIconButton from "@/components/ui/AppIconButton.vue";
  import ThemeToggleButton from "@/components/ui/ThemeToggleButton.vue";
  import { useApplicationStore } from "@/stores/application";
  import { useAuthStore } from "@/stores/base";
  import { computed } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const route = useRoute();
  const router = useRouter();
  const applicationStore = useApplicationStore();
  const authStore = useAuthStore();

  const navSections = computed<SidebarNavSection[]>(() => [
    {
      key: "main",
      label: "Menu",
      items: [
        { key: "worlds", label: "Observatory", icon: "globe", routeName: "worlds" },
        ...(!authStore.localWorldAccess
          ? [
              { key: "home", label: "Home", icon: "dashboard" as const, routeName: "home" },
              { key: "settings", label: "Settings", icon: "settings" as const, disabled: true },
            ]
          : []),
      ],
    },
  ]);

  const activeKey = computed(() => (typeof route.name === "string" ? route.name : undefined));

  async function handleSelect(item: SidebarNavItem, closeSidebar?: () => void) {
    if (item.routeName) {
      await router.push({ name: item.routeName });
    }

    closeSidebar?.();
  }

  async function handleLogout() {
    await authStore.logout();
    await router.push({ name: "login" });
  }
</script>
