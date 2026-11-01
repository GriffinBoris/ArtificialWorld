<template>
  <div class="flex flex-wrap items-start justify-between gap-3">
    <div class="flex min-w-0 flex-1 items-center gap-4">
      <img
        v-if="image"
        :src="image"
        class="h-14 w-14 shrink-0 rounded-xl object-cover"
        alt=""
      />

      <CardHeader
        class="min-w-0 flex-1"
        :eyebrow="eyebrow"
        :title="title"
        :description="description"
        :root-class="headerClass"
        :size="effectiveSize"
      >
        <slot />
      </CardHeader>
    </div>

    <div
      v-if="$slots.actions"
      class="flex shrink-0 flex-wrap justify-end gap-2"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import CardHeader from "@/components/ui/CardHeader.vue";
  import { computed } from "vue";

  interface Props {
    description?: string;
    eyebrow?: string;
    headerClass?: string;
    image?: string;
    size?: "lg" | "md" | "xl";
    title: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    description: undefined,
    eyebrow: undefined,
    headerClass: "max-w-3xl",
    image: undefined,
    size: "lg",
  });

  const effectiveSize = computed(() => (props.image ? "xl" : props.size));
</script>
