<template>
  <button
    :aria-label="collapsed ? label : undefined"
    :data-testid="testId"
    type="button"
    :disabled="disabled"
    :class="buttonClass"
  >
    <span :class="contentClass">
      <AppIcon
        :icon="icon"
        :class="iconClass"
      />
      <span
        class="text-base-body truncate overflow-hidden font-normal transition-all duration-200 ease-in-out"
        :class="collapsed ? 'max-w-0 opacity-0' : 'max-w-[11rem] opacity-100 delay-75'"
      >
        {{ label }}
      </span>
    </span>
    <span
      v-if="badge"
      :class="badgeClass"
    >
      {{ badge }}
    </span>
  </button>
</template>

<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";

  import AppIcon from "@/components/ui/AppIcon.vue";
  import type { AppIconName } from "@/components/ui/appIcons";
  import { cn } from "@/utils/className";
  import { computed } from "vue";

  interface Props {
    active?: boolean;
    badge?: string;
    collapsed?: boolean;
    disabled?: boolean;
    icon: AppIconName | LucideIcon;
    label: string;
    testId?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    active: false,
    badge: undefined,
    collapsed: false,
    disabled: false,
    testId: undefined,
  });

  const buttonClass = computed(() => {
    return cn(
      "group flex text-left transition-colors duration-150 ease-out",
      props.collapsed
        ? "mx-auto h-8 w-8 items-center justify-center rounded-lg p-0"
        : "h-9 w-full items-center justify-between rounded-lg px-2.5 py-0",
      props.disabled
        ? "cursor-not-allowed text-secondary opacity-60"
        : props.active
          ? "bg-line text-body"
          : "text-body/85 hover:bg-line/50 hover:text-body"
    );
  });

  const contentClass = computed(() => {
    return cn("flex min-w-0 items-center", props.collapsed ? "justify-center gap-0" : "gap-3");
  });

  const iconClass = computed(() => {
    return cn(
      "text-control h-[1.05rem] w-[1.05rem]",
      props.active ? "text-body" : "text-secondary group-hover:text-body"
    );
  });

  const badgeClass = computed(() => {
    return cn(
      "text-muted overflow-hidden rounded-full border px-2 py-0.5 font-medium transition-all duration-200 ease-in-out",
      props.collapsed ? "max-w-0 border-transparent px-0 opacity-0" : "max-w-[4rem] opacity-100 delay-75",
      props.active ? "border-line bg-surface text-secondary" : "border-line bg-surface/80 text-secondary"
    );
  });
</script>
