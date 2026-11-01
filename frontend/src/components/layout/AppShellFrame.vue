<template>
  <div :class="shellClass">
    <aside class="border-line bg-surface-muted hidden min-h-0 border-r lg:block">
      <slot
        :is-sidebar-collapsed="isDesktopSidebarCollapsed"
        :close-sidebar="undefined"
        sidebar-mode="desktop"
        name="sidebar"
      />
    </aside>

    <div class="bg-background flex min-h-0 min-w-0 flex-col">
      <AppMobileShellBar @open-sidebar="isMobileSidebarOpen = true" />

      <AppMobileSidebarDrawer
        :open="isMobileSidebarOpen"
        @close="isMobileSidebarOpen = false"
      >
        <slot
          name="sidebar"
          :is-sidebar-collapsed="false"
          :close-sidebar="closeMobileSidebar"
          sidebar-mode="mobile"
        />
      </AppMobileSidebarDrawer>

      <div class="min-h-0 min-w-0 flex-1">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import AppMobileShellBar from "@/components/layout/AppMobileShellBar.vue";
  import AppMobileSidebarDrawer from "@/components/layout/AppMobileSidebarDrawer.vue";
  import { cn } from "@/utils/className";
  import { computed, ref } from "vue";

  const isMobileSidebarOpen = ref(false);
  const isDesktopSidebarCollapsed = ref(false);

  function closeMobileSidebar() {
    isMobileSidebarOpen.value = false;
  }

  const shellClass = computed(() => {
    return cn(
      "grid h-full min-h-0 transition-[grid-template-columns] duration-300 ease-in-out",
      isDesktopSidebarCollapsed.value ? "lg:grid-cols-[4.25rem_minmax(0,1fr)]" : "lg:grid-cols-[15.5rem_minmax(0,1fr)]"
    );
  });

  defineExpose({
    isDesktopSidebarCollapsed,
    closeMobileSidebar,
    toggleDesktopSidebar() {
      isDesktopSidebarCollapsed.value = !isDesktopSidebarCollapsed.value;
    },
  });
</script>
