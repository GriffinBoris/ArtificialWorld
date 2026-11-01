<template>
  <dialog
    ref="dialog"
    class="game-dialog"
    :class="{ 'game-dialog-wide': wide, 'game-dialog-fullscreen': fullscreen }"
    :aria-label="label"
    @keydown.stop
    @cancel.prevent.stop="emit('close')"
    @click.self="outsideClick"
  >
    <slot />
  </dialog>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, onMounted, ref } from "vue";
  defineProps<{ label: string; wide?: boolean; fullscreen?: boolean }>();
  const emit = defineEmits<{ close: [] }>();
  const dialog = ref<HTMLDialogElement>();
  function outsideClick(event: MouseEvent) {
    const bounds = dialog.value?.getBoundingClientRect();

    if (
      bounds &&
      (event.clientX < bounds.left ||
        event.clientX > bounds.right ||
        event.clientY < bounds.top ||
        event.clientY > bounds.bottom)
    )
      emit("close");
  }
  onMounted(() => dialog.value?.showModal());
  onBeforeUnmount(() => dialog.value?.close());
</script>
