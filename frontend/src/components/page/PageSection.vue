<template>
  <AppSurface :root-class="rootClass || 'shadow-none'">
    <CardHeader
      v-if="title"
      :eyebrow="eyebrow"
      :title="title"
      :description="description"
    />

    <div :class="contentClass">
      <slot />
    </div>
  </AppSurface>
</template>

<script setup lang="ts">
  import AppSurface from "@/components/ui/AppSurface.vue";
  import CardHeader from "@/components/ui/CardHeader.vue";

  interface Props {
    contentClass?: string;
    description?: string;
    eyebrow?: string;
    rootClass?: string;
    title?: string;
  }

  withDefaults(defineProps<Props>(), {
    contentClass: "mt-4",
    description: undefined,
    eyebrow: undefined,
    rootClass: undefined,
    title: undefined,
  });
</script>
