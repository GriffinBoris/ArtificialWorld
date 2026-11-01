<template>
  <a
    v-if="href"
    :href="linkHref"
    :target="target"
    :rel="linkRel"
    :aria-label="ariaLabel"
    :aria-controls="ariaControls"
    :aria-haspopup="ariaHaspopup"
    :aria-disabled="isDisabled || undefined"
    :class="buttonPt.root"
    :tabindex="isDisabled ? -1 : undefined"
    :data-testid="testId"
    @click="handleLinkClick"
  >
    <template v-if="$slots.default">
      <slot />
    </template>

    <template v-else>
      <AppIcon
        v-if="loading"
        icon="refresh"
        class="text-control h-4 w-4 animate-spin"
      />
      <AppIcon
        v-else-if="icon"
        :icon="icon"
        class="text-control h-4 w-4"
      />
      <span
        v-if="label"
        class="font-medium"
      >
        {{ label }}
      </span>
    </template>
  </a>

  <Button
    v-else
    unstyled
    :type="buttonType"
    :aria-label="ariaLabel"
    :aria-controls="ariaControls"
    :aria-haspopup="ariaHaspopup"
    :disabled="disabled"
    :form="form"
    :label="label"
    :loading="loading"
    :pt="buttonPt"
    :data-testid="testId"
  >
    <template
      v-if="loading"
      #loadingicon
    >
      <AppIcon
        icon="refresh"
        class="text-control h-4 w-4 animate-spin"
      />
    </template>

    <template
      v-else-if="icon"
      #icon
    >
      <AppIcon
        :icon="icon"
        class="text-control h-4 w-4"
      />
    </template>

    <template
      v-if="$slots.default"
      #default
    >
      <slot />
    </template>
  </Button>
</template>

<script setup lang="ts">
  import type { LucideIcon } from "@lucide/vue";

  import AppIcon from "@/components/ui/AppIcon.vue";
  import { cn } from "@/utils/className";
  import Button from "primevue/button";
  import { computed } from "vue";

  import type { AppIconName } from "@/components/ui/appIcons";

  type AppButtonTone = "primary" | "secondary" | "ghost" | "link";
  type AppButtonSize = "sm" | "md";

  interface Props {
    ariaControls?: string;
    ariaLabel?: string;
    ariaHaspopup?: boolean | "menu" | "dialog" | "grid" | "listbox" | "tree";
    buttonType?: "button" | "reset" | "submit";
    disabled?: boolean;
    form?: string;
    href?: string;
    icon?: AppIconName | LucideIcon;
    iconPos?: "left" | "right" | "top" | "bottom";
    label?: string;
    loading?: boolean;
    rootClass?: string;
    size?: AppButtonSize;
    target?: "_blank" | "_parent" | "_self" | "_top";
    testId?: string;
    tone?: AppButtonTone;
  }

  const props = withDefaults(defineProps<Props>(), {
    ariaControls: undefined,
    ariaLabel: undefined,
    ariaHaspopup: undefined,
    buttonType: "button",
    disabled: false,
    form: undefined,
    href: undefined,
    icon: undefined,
    iconPos: "left",
    label: undefined,
    loading: false,
    rootClass: undefined,
    size: "md",
    target: undefined,
    testId: undefined,
    tone: "secondary",
  });

  const isDisabled = computed(() => props.disabled || props.loading);
  const linkHref = computed(() => (isDisabled.value ? undefined : props.href));
  const linkRel = computed(() => (props.target === "_blank" ? "noopener noreferrer" : undefined));

  function handleLinkClick(event: MouseEvent) {
    if (isDisabled.value) {
      event.preventDefault();
    }
  }

  const sizeClasses = computed(() => {
    if (props.tone === "link") {
      return "gap-1.5 px-0 py-0 text-control";
    }

    return props.size === "sm" ? "gap-1.5 px-3 text-control min-h-9" : "gap-1.5 px-3.5 text-control min-h-10";
  });

  const toneClasses = computed(() => {
    if (props.tone === "primary") {
      return "border border-primary bg-primary text-primary-contrast shadow-xs hover:bg-primary/90";
    }

    if (props.tone === "ghost") {
      return "bg-surface-muted text-body hover:bg-line";
    }

    if (props.tone === "link") {
      return "border border-transparent bg-transparent text-secondary shadow-none hover:bg-transparent hover:text-body";
    }

    return "border border-line bg-surface text-body shadow-xs hover:border-body/15 hover:bg-surface-muted";
  });

  const buttonPt = computed(() => ({
    root: cn(
      "inline-flex items-center rounded-md font-medium transition-colors duration-200 ease-out focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-focus-ring/20 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:cursor-not-allowed disabled:opacity-60",
      sizeClasses.value,
      toneClasses.value,
      isDisabled.value && "cursor-not-allowed opacity-60",
      props.rootClass
    ),
    loadingIcon: "text-control",
    icon: "text-control",
    label: "font-medium",
  }));
</script>
