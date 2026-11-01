<template>
  <AppButton
    :label="iconOnly ? undefined : label"
    :aria-label="label"
    :title="iconOnly ? label : undefined"
    :icon="icon"
    :disabled="disabled"
    :loading="loading"
    :button-type="buttonType"
    :test-id="testId"
    :root-class="`game-button ${primary ? 'game-button-primary' : ''} ${iconOnly ? 'game-icon-button' : ''} ${active ? 'is-active' : ''}`"
  />
</template>
<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import type { LucideIcon } from "@lucide/vue";
  withDefaults(
    defineProps<{
      label: string;
      icon?: LucideIcon;
      iconOnly?: boolean;
      primary?: boolean;
      active?: boolean;
      disabled?: boolean;
      loading?: boolean;
      buttonType?: "button" | "submit";
      testId?: string;
    }>(),
    {
      icon: undefined,
      iconOnly: false,
      primary: false,
      active: false,
      disabled: false,
      loading: false,
      buttonType: "button",
      testId: undefined,
    }
  );
</script>
