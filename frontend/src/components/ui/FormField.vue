<template>
  <label
    :for="inputId"
    :class="cn('block space-y-2', rootClass)"
  >
    <div
      v-if="label || optionalLabel"
      class="flex items-center justify-between gap-3"
    >
      <span class="text-body text-sm font-medium">{{ label }}</span>
      <span
        v-if="optionalLabel"
        class="text-secondary text-eyebrow font-medium uppercase"
        >{{ optionalLabel }}</span
      >
    </div>

    <slot />

    <p
      v-if="error"
      class="text-error text-sm"
    >
      {{ error }}
    </p>
    <p
      v-else-if="hint"
      class="text-secondary text-sm"
    >
      {{ hint }}
    </p>
  </label>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";

  interface Props {
    error?: string;
    hint?: string;
    inputId?: string;
    label?: string;
    optionalLabel?: string;
    rootClass?: string;
  }

  withDefaults(defineProps<Props>(), {
    error: undefined,
    hint: undefined,
    inputId: undefined,
    label: undefined,
    optionalLabel: undefined,
    rootClass: undefined,
  });
</script>
