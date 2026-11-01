<template>
  <div :class="cn('space-y-1.5', rootClass)">
    <p
      v-if="eyebrow"
      :class="cn('text-secondary text-eyebrow font-medium uppercase', eyebrowClass)"
    >
      {{ eyebrow }}
    </p>

    <div class="space-y-0.5">
      <component
        :is="titleTag"
        :class="cn(titleSizeClass, 'text-body font-semibold', titleClass)"
      >
        {{ title }}
      </component>

      <p
        v-if="description"
        :class="cn(descriptionSizeClass, 'text-secondary', descriptionClass)"
      >
        {{ description }}
      </p>
    </div>

    <slot />
  </div>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import { computed } from "vue";

  interface Props {
    description?: string;
    descriptionClass?: string;
    eyebrow?: string;
    eyebrowClass?: string;
    rootClass?: string;
    size?: "lg" | "md" | "xl";
    title: string;
    titleClass?: string;
    titleTag?: "h1" | "h2" | "h3";
  }

  const props = withDefaults(defineProps<Props>(), {
    description: undefined,
    descriptionClass: undefined,
    eyebrow: undefined,
    eyebrowClass: undefined,
    rootClass: undefined,
    size: "md",
    titleClass: undefined,
    titleTag: "h2",
  });

  const titleSizeClass = computed(() => {
    if (props.size === "xl") return "text-3xl font-bold tracking-tight";

    return props.size === "lg" ? "text-heading-lg tracking-[-0.02em]" : "text-heading-sm";
  });

  const descriptionSizeClass = computed(() => {
    return props.size === "xl" || props.size === "lg" ? "text-base-body" : "text-muted";
  });
</script>
