<template>
  <RouterView
    v-if="route.meta.immersive"
    :key="routerViewKey"
  />

  <GuestPageShell v-else-if="isGuestRoute">
    <RouterView />
  </GuestPageShell>

  <AppShellView v-else>
    <RouterView :key="routerViewKey" />
  </AppShellView>

  <AppToastViewport />
</template>

<script setup lang="ts">
  import AppToastViewport from "@/components/layout/AppToastViewport.vue";
  import GuestPageShell from "@/components/layout/GuestPageShell.vue";
  import AppShellView from "@/views/AppShell/AppShellView.vue";
  import { computed } from "vue";
  import { RouterView, useRoute } from "vue-router";

  const route = useRoute();

  const isGuestRoute = computed(() => Boolean(route.meta.guestOnly));
  const routerViewKey = computed(() => String(route.name ?? route.fullPath));
</script>
