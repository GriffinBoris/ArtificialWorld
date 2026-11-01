<template>
  <Transition
    enter-active-class="transition-opacity duration-200 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open"
      class="bg-body/20 fixed inset-0 z-40 lg:hidden"
      :aria-label="closeLabel"
      @click="emit('close')"
    />
  </Transition>

  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="-translate-x-4 opacity-0"
    enter-to-class="translate-x-0 opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="translate-x-0 opacity-100"
    leave-to-class="-translate-x-3 opacity-0"
  >
    <div
      v-if="open"
      class="fixed inset-y-0 left-0 z-50 w-[15.5rem] max-w-[calc(100vw-1.5rem)] lg:hidden"
      aria-modal="true"
      role="dialog"
    >
      <div
        class="border-line bg-surface-muted/98 flex h-full min-h-0 flex-col overflow-hidden border-r shadow-xl backdrop-blur-xs"
      >
        <div class="min-h-0 flex-1 overflow-hidden">
          <slot />
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
  interface Props {
    closeLabel?: string;
    open?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    closeLabel: "Close navigation",
    open: false,
  });

  const emit = defineEmits<{
    close: [];
  }>();
</script>
