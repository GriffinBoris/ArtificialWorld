<template>
  <main class="h-full min-h-0 min-w-0 overflow-hidden">
    <div class="h-full overflow-x-hidden overflow-y-auto">
      <div :class="contentClass">
        <slot />
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
  interface Props {
    contentClass?: string;
  }

  withDefaults(defineProps<Props>(), {
    contentClass: "flex min-h-full flex-col gap-4",
  });
</script>
