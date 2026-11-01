import { defineStore } from "pinia";
import { ref } from "vue";

export type ApplicationNotificationTone = "error" | "info" | "success" | "warning";

export interface ApplicationNotification {
  createdAt: number;
  durationMs: number;
  id: string;
  message: string;
  title: string;
  tone: ApplicationNotificationTone;
}

interface ShowNotificationInput {
  durationMs?: number;
  message: string;
  title: string;
  tone: ApplicationNotificationTone;
}

const defaultDurationMs = 4000;

export const useNotificationsStore = defineStore("notifications", () => {
  const notifications = ref<ApplicationNotification[]>([]);
  const dismissTimers = new Map<string, ReturnType<typeof window.setTimeout>>();

  function clearDismissTimer(notificationId: string) {
    const timer = dismissTimers.get(notificationId);

    if (timer === undefined) {
      return;
    }

    window.clearTimeout(timer);
    dismissTimers.delete(notificationId);
  }

  function scheduleDismiss(notification: ApplicationNotification) {
    clearDismissTimer(notification.id);

    if (notification.durationMs <= 0) {
      return;
    }

    const timer = window.setTimeout(() => {
      dismiss(notification.id);
    }, notification.durationMs);

    dismissTimers.set(notification.id, timer);
  }

  function show({ durationMs = defaultDurationMs, message, title, tone }: ShowNotificationInput) {
    const notification: ApplicationNotification = {
      createdAt: Date.now(),
      durationMs,
      id: crypto.randomUUID(),
      message,
      title,
      tone,
    };

    notifications.value = [...notifications.value, notification];
    scheduleDismiss(notification);

    return notification.id;
  }

  function dismiss(notificationId: string) {
    clearDismissTimer(notificationId);
    notifications.value = notifications.value.filter((notification) => notification.id !== notificationId);
  }

  function pushError(title: string, message: string, durationMs = 5000) {
    return show({ durationMs, message, title, tone: "error" });
  }

  function pushInfo(title: string, message: string, durationMs = defaultDurationMs) {
    return show({ durationMs, message, title, tone: "info" });
  }

  function pushSuccess(title: string, message: string, durationMs = defaultDurationMs) {
    return show({ durationMs, message, title, tone: "success" });
  }

  function pushWarning(title: string, message: string, durationMs = 4500) {
    return show({ durationMs, message, title, tone: "warning" });
  }

  return {
    dismiss,
    notifications,
    pushError,
    pushInfo,
    pushSuccess,
    pushWarning,
    show,
  };
});
