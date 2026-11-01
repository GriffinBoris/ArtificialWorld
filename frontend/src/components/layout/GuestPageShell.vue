<template>
  <AppContainer>
    <div class="h-full min-h-0 overflow-x-hidden overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4 sm:p-6 lg:p-8">
        <slot />
      </div>
    </div>
  </AppContainer>
</template>

<script setup lang="ts">
  import AppContainer from "@/components/layout/AppContainer.vue";
</script>
