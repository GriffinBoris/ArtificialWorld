<template>
  <div
    class="space-y-2"
    :class="{ 'text-center': centered }"
  >
    <p
      v-if="eyebrow"
      class="text-secondary text-eyebrow font-medium uppercase"
    >
      {{ eyebrow }}
    </p>

    <h1 class="text-body text-2xl font-semibold tracking-tight">{{ title }}</h1>

    <p
      v-if="description"
      class="text-secondary text-sm leading-6"
    >
      {{ description }}
    </p>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    centered?: boolean;
    description?: string;
    eyebrow?: string;
    title: string;
  }

  withDefaults(defineProps<Props>(), {
    centered: false,
    description: undefined,
    eyebrow: undefined,
  });
</script>
