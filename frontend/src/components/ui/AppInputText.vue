<template>
  <InputText
    :id="inputId"
    :model-value="modelValue"
    unstyled
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    :autocomplete="autocomplete"
    :pt="inputPt"
    :data-testid="testId"
    class="w-full"
    @update:model-value="onUpdateModelValue"
  />
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import InputText from "primevue/inputtext";
  import { computed } from "vue";

  interface Props {
    autocomplete?: string;
    disabled?: boolean;
    hasError?: boolean;
    inputClass?: string;
    inputId?: string;
    modelValue: string;
    placeholder?: string;
    testId?: string;
    type?: "date" | "email" | "number" | "password" | "search" | "tel" | "text" | "url";
  }

  const props = withDefaults(defineProps<Props>(), {
    autocomplete: undefined,
    disabled: false,
    hasError: false,
    inputClass: undefined,
    inputId: undefined,
    placeholder: undefined,
    testId: undefined,
    type: "text",
  });

  const emit = defineEmits<{
    "update:modelValue": [value: string];
  }>();

  const inputPt = computed(() => ({
    root: cn(
      "w-full border border-line bg-surface px-3 text-control text-body shadow-none transition-colors duration-200 ease-out placeholder:text-secondary focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-focus-ring/15 disabled:cursor-not-allowed disabled:opacity-60",
      "min-h-10 rounded-md",
      props.hasError ? "border-error/60 ring-1 ring-error/15" : undefined,
      props.inputClass
    ),
  }));

  function onUpdateModelValue(value: string | undefined) {
    emit("update:modelValue", value ?? "");
  }
</script>
