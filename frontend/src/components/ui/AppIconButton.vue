<template>
  <AppButton
    :aria-controls="ariaControls"
    :aria-haspopup="ariaHaspopup"
    :button-type="buttonType"
    :disabled="disabled"
    :icon="icon"
    :loading="loading"
    :root-class="iconButtonClass"
    :test-id="testId"
    :aria-label="label"
    v-tooltip="tooltipBinding"
    @click="handleClick"
  />
</template>

<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";

  import AppButton from "@/components/ui/AppButton.vue";
  import type { AppIconName } from "@/components/ui/appIcons";
  import { buildAppTooltipBinding } from "@/components/ui/AppTooltip";
  import { cn } from "@/utils/className";
  import { computed } from "vue";

  interface Props {
    ariaControls?: string;
    ariaHaspopup?: boolean | "menu" | "dialog" | "grid" | "listbox" | "tree";
    buttonType?: "button" | "reset" | "submit";
    danger?: boolean;
    disabled?: boolean;
    icon: AppIconName | LucideIcon;
    label: string;
    loading?: boolean;
    rootClass?: string;
    rounded?: boolean;
    tone?: "default" | "ghost";
    testId?: string;
    tooltipDelay?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    ariaControls: undefined,
    ariaHaspopup: undefined,
    buttonType: "button",
    danger: false,
    disabled: false,
    loading: false,
    rootClass: undefined,
    rounded: false,
    testId: undefined,
    tone: "default",
    tooltipDelay: 200,
  });

  const emit = defineEmits<{
    click: [event: MouseEvent];
  }>();

  const iconButtonClass = computed(() => {
    const baseClass =
      props.tone === "ghost"
        ? "h-9 w-9 justify-center border-transparent bg-transparent p-0 shadow-none hover:bg-surface-muted"
        : "h-9 w-9 justify-center border border-line bg-surface p-0 shadow-xs hover:bg-surface-muted";

    return cn(
      baseClass,
      props.rounded ? "rounded-full" : "rounded-md",
      props.danger ? "text-error hover:border-error/20 hover:bg-error/8" : "text-body",
      props.rootClass
    );
  });

  const tooltipBinding = computed(() => {
    return buildAppTooltipBinding({
      delay: props.tooltipDelay,
      disabled: props.disabled,
      text: props.label,
    });
  });

  function handleClick(event: MouseEvent) {
    emit("click", event);
  }
</script>
