<template>
  <Tag
    unstyled
    :value="value"
    :pt="tagPt"
  >
    <slot />
  </Tag>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import Tag from "primevue/tag";
  import { computed } from "vue";

  type AppTagTone = "info" | "neutral" | "success" | "warning";
  type AppTagSize = "sm" | "md";

  interface Props {
    size?: AppTagSize;
    tone?: AppTagTone;
    value?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    size: "md",
    tone: "neutral",
    value: undefined,
  });

  const toneClasses = computed(() => {
    const toneMap: Record<AppTagTone, string> = {
      neutral: "border-line bg-surface text-body",
      info: "border-info/15 bg-info/8 text-info",
      success: "border-success/30 bg-success/10 text-success",
      warning: "border-warning/20 bg-warning/10 text-warning",
    };

    return toneMap[props.tone];
  });

  const sizeClasses = computed(() => {
    return props.size === "sm" ? "px-1.5 py-px text-[0.6875rem] leading-4" : "px-2 py-0.5 text-[0.75rem] leading-4";
  });

  const tagPt = computed(() => ({
    root: cn("inline-flex items-center rounded-full border font-normal", sizeClasses.value, toneClasses.value),
    label: "font-normal",
  }));
</script>
