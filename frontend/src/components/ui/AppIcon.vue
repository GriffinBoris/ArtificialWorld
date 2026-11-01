<template>
  <component
    :is="resolvedIcon"
    v-if="resolvedIcon"
    :class="iconClass"
    :stroke-width="strokeWidth"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";
  import { computed } from "vue";

  import { type AppIconName, appIcons } from "@/components/ui/appIcons";
  import { cn } from "@/utils/className";

  interface Props {
    class?: string;
    icon: AppIconName | LucideIcon;
    strokeWidth?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    class: undefined,
    strokeWidth: 2,
  });

  const resolvedIcon = computed(() => {
    if (typeof props.icon === "string") {
      return appIcons[props.icon] ?? null;
    }

    return props.icon;
  });

  const iconClass = computed(() => {
    return cn("shrink-0", props.class);
  });
</script>
