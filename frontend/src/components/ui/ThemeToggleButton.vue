<template>
  <AppButton
    :aria-label="ariaLabel"
    :icon="buttonIcon"
    :label="buttonLabel"
    :root-class="rootClass"
    size="sm"
    tone="ghost"
    @click="themeStore.toggleTheme"
  />
</template>

<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import type { AppIconName } from "@/components/ui/appIcons";
  import { useThemeStore } from "@/stores/theme";
  import { computed } from "vue";

  interface Props {
    rootClass?: string;
    showLabel?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    rootClass: undefined,
    showLabel: false,
  });

  const themeStore = useThemeStore();

  const buttonIcon = computed<AppIconName>(() => (themeStore.isDark ? "sun" : "moon"));
  const buttonLabel = computed(() => {
    if (!props.showLabel) {
      return undefined;
    }

    return themeStore.isDark ? "Light mode" : "Dark mode";
  });
  const ariaLabel = computed(() => (themeStore.isDark ? "Switch to light mode" : "Switch to dark mode"));
</script>
