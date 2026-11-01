<template>
  <div class="border-line bg-background/95 border-b px-4 py-3 lg:hidden">
    <div class="flex items-center justify-between gap-3">
      <div class="min-w-0">
        <p class="text-body text-eyebrow font-semibold tracking-[0.04em] uppercase">{{ eyebrow }}</p>
        <p class="text-body text-base-body truncate font-medium">{{ title }}</p>
      </div>

      <AppIconButton
        icon="menu"
        :label="buttonLabel"
        root-class="h-10 w-10"
        @click="emit('open-sidebar')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
  import AppIconButton from "@/components/ui/AppIconButton.vue";

  interface Props {
    buttonLabel?: string;
    eyebrow?: string;
    title?: string;
  }

  withDefaults(defineProps<Props>(), {
    buttonLabel: "Open navigation",
    eyebrow: "App",
    title: "Workspace",
  });

  const emit = defineEmits<{
    "open-sidebar": [];
  }>();
</script>
