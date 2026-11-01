<template>
  <nav class="flex h-full min-h-0 flex-col">
    <div :class="headerClass">
      <slot name="header">
        <div>
          <p class="text-body text-sm font-semibold">Workspace</p>
        </div>
      </slot>
    </div>

    <div class="min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-1.5 py-2">
      <div :class="collapsed ? 'space-y-2.5' : 'space-y-3'">
        <section
          v-for="section in sections"
          :key="section.key"
          :class="sectionClass"
        >
          <div
            v-if="showSectionHeader(section)"
            :data-testid="`sidebar-section-${section.key}`"
            :class="sectionButtonClass()"
          >
            <span :class="sectionHeaderClass()">{{ section.label }}</span>
          </div>

          <div
            v-if="section.items.length > 0"
            :class="sectionItemsClass()"
          >
            <AppSidebarNavItem
              v-for="item in section.items"
              :key="item.key"
              :active="activeKey === item.key"
              :badge="item.badge"
              :collapsed="collapsed"
              :disabled="item.disabled"
              :icon="item.icon"
              :label="item.label"
              :test-id="`sidebar-item-${item.key}`"
              @click="emit('select', item)"
            />
          </div>
        </section>
      </div>
    </div>

    <div
      v-if="$slots.footer"
      :class="footerClass"
    >
      <slot name="footer" />
    </div>
  </nav>
</template>

<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";

  import AppSidebarNavItem from "@/components/navigation/AppSidebarNavItem.vue";
  import type { AppIconName } from "@/components/ui/appIcons";
  import { cn } from "@/utils/className";
  import { computed } from "vue";

  export interface SidebarNavItem {
    badge?: string;
    disabled?: boolean;
    icon: AppIconName | LucideIcon;
    key: string;
    label: string;
    routeQuery?: Record<string, number | string>;
    routeParams?: Record<string, number | string>;
    routeName?: string;
  }

  export interface SidebarNavSection {
    items: SidebarNavItem[];
    key: string;
    label?: string;
  }

  interface Props {
    activeKey?: string;
    collapsed?: boolean;
    sections: SidebarNavSection[];
  }

  const props = withDefaults(defineProps<Props>(), {
    activeKey: undefined,
    collapsed: false,
  });

  const emit = defineEmits<{
    select: [item: SidebarNavItem];
  }>();

  const headerClass = computed(() => {
    return cn(
      "transition-[padding] duration-300 ease-in-out",
      props.collapsed ? "px-3 pb-1.5 pt-3.5" : "px-4 pb-1.5 pt-3.5"
    );
  });

  const footerClass = computed(() => {
    return cn(
      "mt-auto transition-[padding] duration-300 ease-in-out",
      props.collapsed ? "px-1.5 pb-1.5 pt-1" : "px-1.5 pb-1.5 pt-1"
    );
  });

  const sectionClass = computed(() => {
    return cn("space-y-1");
  });

  function showSectionHeader(section: SidebarNavSection) {
    return !props.collapsed && Boolean(section.label);
  }

  function sectionHeaderClass() {
    return cn("px-2.5 pb-0 pt-0 text-muted font-normal text-secondary");
  }

  function sectionButtonClass() {
    return cn("flex w-full items-center rounded-lg px-0 py-0 text-left");
  }

  function sectionItemsClass() {
    return cn("space-y-1");
  }
</script>
