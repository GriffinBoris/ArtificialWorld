<template>
  <FormField
    :label="label"
    :hint="hint"
    :error="error"
    :input-id="inputId"
    :optional-label="optionalLabel"
    :root-class="rootClass"
  >
    <AppInputText
      :input-id="inputId"
      :model-value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :autocomplete="autocomplete"
      :has-error="Boolean(error)"
      :test-id="testId"
      @update:model-value="onUpdateModelValue"
    />
  </FormField>
</template>

<script setup lang="ts">
  import AppInputText from "@/components/ui/AppInputText.vue";
  import FormField from "@/components/ui/FormField.vue";

  interface Props {
    autocomplete?: string;
    disabled?: boolean;
    error?: string;
    hint?: string;
    inputId?: string;
    label: string;
    modelValue: string;
    optionalLabel?: string;
    placeholder?: string;
    rootClass?: string;
    testId?: string;
    type?: "date" | "email" | "number" | "password" | "search" | "tel" | "text" | "url";
  }

  withDefaults(defineProps<Props>(), {
    autocomplete: undefined,
    disabled: false,
    error: undefined,
    hint: undefined,
    inputId: undefined,
    optionalLabel: undefined,
    placeholder: undefined,
    rootClass: undefined,
    testId: undefined,
    type: "text",
  });

  const emit = defineEmits<{
    "update:modelValue": [value: string];
  }>();

  function onUpdateModelValue(value: string | undefined) {
    emit("update:modelValue", value ?? "");
  }
</script>
