<template>
  <Select
    :input-id="inputId"
    :aria-label="ariaLabel"
    :model-value="modelValue"
    unstyled
    :options="options"
    :option-label="optionLabel"
    :option-value="optionValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :pt="selectPt"
    :overlay-class="overlayClass"
    :data-testid="testId"
    class="app-select w-full"
    @update:model-value="onUpdateModelValue"
  />
</template>

<script setup lang="ts" generic="TOption extends object, TValue = unknown">
  import { cn } from "@/utils/className";
  import Select from "primevue/select";
  import { computed } from "vue";

  const props = withDefaults(
    defineProps<{
      disabled?: boolean;
      ariaLabel?: string;
      overlayClass?: string;
      hasError?: boolean;
      inputId?: string;
      modelValue: TValue | null;
      optionLabel: keyof TOption & string;
      optionValue: keyof TOption & string;
      options: TOption[];
      placeholder?: string;
      rootClass?: string;
      testId?: string;
    }>(),
    {
      disabled: false,
      ariaLabel: undefined,
      overlayClass: undefined,
      hasError: false,
      inputId: undefined,
      placeholder: undefined,
      rootClass: undefined,
      testId: undefined,
    }
  );

  const emit = defineEmits<{
    "update:modelValue": [value: TValue | null];
  }>();

  const selectPt = computed(() => ({
    root: cn(
      "flex cursor-pointer items-center border border-line pl-3 text-control text-body shadow-none transition-colors duration-200 ease-out focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-focus-ring/15",
      "min-h-11 rounded-md bg-surface",
      props.disabled ? "cursor-not-allowed opacity-60" : undefined,
      props.hasError ? "border-error/60 ring-1 ring-error/15" : undefined,
      props.rootClass
    ),
    label:
      "flex min-h-11 min-w-0 flex-1 items-center truncate text-control text-body outline-none placeholder:text-secondary",
    dropdown: "pointer-events-none flex w-11 shrink-0 self-stretch items-center justify-center text-secondary",
    overlay: "rounded-lg border border-line bg-surface p-1 shadow-lg",
    list: "space-y-0.5",
    option:
      "flex min-h-11 cursor-pointer items-center rounded-md px-3 py-2 text-control text-body transition-colors hover:bg-line/40 data-[p-focused=true]:bg-line/60 aria-selected:bg-line/60",
    optionLabel: "truncate",
    emptyMessage: "px-3 py-2 text-sm text-secondary",
  }));

  function onUpdateModelValue(value: TValue | null) {
    emit("update:modelValue", value);
  }
</script>
