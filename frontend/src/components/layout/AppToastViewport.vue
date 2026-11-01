<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed inset-x-4 top-4 z-[70] flex justify-end sm:inset-x-6"
      aria-live="polite"
      aria-relevant="additions text"
    >
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="translate-y-2 opacity-0"
        enter-to-class="translate-y-0 opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="translate-y-0 opacity-100"
        leave-to-class="translate-y-2 opacity-0"
        move-class="transition duration-200 ease-out"
        tag="div"
        class="flex w-full max-w-sm flex-col gap-3"
      >
        <div
          v-for="notification in notificationsStore.notifications"
          :key="notification.id"
          class="pointer-events-auto"
          :role="notification.tone === 'error' ? 'alert' : 'status'"
        >
          <AppSurface
            :root-class="toastRootClass(notification.tone)"
            content-class="p-4"
          >
            <div class="flex items-start gap-3">
              <div
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                :class="toastIconWrapperClass(notification.tone)"
              >
                <AppIcon
                  :icon="toastIcon(notification.tone)"
                  class="h-4 w-4"
                />
              </div>

              <div class="min-w-0 flex-1 space-y-1">
                <p class="text-body text-sm font-semibold">{{ notification.title }}</p>
                <p class="text-secondary text-sm leading-6">{{ notification.message }}</p>
              </div>

              <AppIconButton
                icon="close"
                label="Dismiss notification"
                tone="ghost"
                root-class="h-8 w-8 shrink-0 hover:bg-line/50"
                @click="notificationsStore.dismiss(notification.id)"
              />
            </div>
          </AppSurface>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import type { AppIconName } from "@/components/ui/appIcons";

  import AppIconButton from "@/components/ui/AppIconButton.vue";
  import AppIcon from "@/components/ui/AppIcon.vue";
  import AppSurface from "@/components/ui/AppSurface.vue";
  import type { ApplicationNotificationTone } from "@/stores/notifications";
  import { useNotificationsStore } from "@/stores/notifications";

  const notificationsStore = useNotificationsStore();

  function toastRootClass(tone: ApplicationNotificationTone) {
    if (tone === "success") {
      return "border-success/20";
    }

    if (tone === "warning") {
      return "border-warning/20";
    }

    if (tone === "info") {
      return "border-info/20";
    }

    return "border-error/20";
  }

  function toastIcon(tone: ApplicationNotificationTone): AppIconName {
    if (tone === "success") {
      return "success";
    }

    if (tone === "warning") {
      return "warning";
    }

    if (tone === "info") {
      return "info";
    }

    return "close";
  }

  function toastIconWrapperClass(tone: ApplicationNotificationTone) {
    if (tone === "success") {
      return "bg-success/12 text-success";
    }

    if (tone === "warning") {
      return "bg-warning/12 text-warning";
    }

    if (tone === "info") {
      return "bg-info/12 text-info";
    }

    return "bg-error/12 text-error";
  }
</script>
