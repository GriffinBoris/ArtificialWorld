<template>
  <Message
    unstyled
    :severity="severity"
    :pt="messagePt"
  >
    {{ message }}
  </Message>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import Message from "primevue/message";
  import { computed } from "vue";

  interface Props {
    message: string;
    tone?: "error" | "success" | "warning";
  }

  const props = withDefaults(defineProps<Props>(), { tone: "error" });

  const severity = computed(() => {
    if (props.tone === "success") {
      return "success";
    }

    if (props.tone === "warning") {
      return "warn";
    }

    return "error";
  });

  const rootClasses = computed(() => {
    if (props.tone === "success") {
      return "border-success/20 bg-success/10 text-success";
    }

    if (props.tone === "warning") {
      return "border-warning/20 bg-warning/10 text-warning";
    }

    return "border-error/20 bg-error/10 text-error";
  });

  const messagePt = computed(() => ({
    root: cn("w-full rounded-md border px-4 py-3 text-sm", rootClasses.value),
    contentWrapper: "w-full",
    content: "w-full",
    text: "leading-6",
  }));
</script>
