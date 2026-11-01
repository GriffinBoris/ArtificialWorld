import type { DirectiveBinding } from "vue";

export interface AppTooltipOptions {
  delay?: number;
  disabled?: boolean;
  text: string;
}

function normalizeTooltipBinding(value: AppTooltipOptions | string) {
  if (typeof value === "string") {
    return {
      disabled: false,
      pt: {
        arrow: "hidden",
        text: "rounded-md bg-body px-2.5 py-1.5 text-xs font-medium text-primary-contrast shadow-lg",
      },
      showDelay: 150,
      value,
    };
  }

  return {
    disabled: value.disabled ?? false,
    pt: {
      arrow: "hidden",
      text: "rounded-md bg-body px-2.5 py-1.5 text-xs font-medium text-primary-contrast shadow-lg",
    },
    showDelay: value.delay ?? 150,
    value: value.text,
  };
}

export function buildAppTooltipBinding(value: AppTooltipOptions | string): DirectiveBinding["value"] {
  return normalizeTooltipBinding(value);
}
