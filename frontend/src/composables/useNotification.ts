import { useNotificationsStore } from "@/stores/notifications";

export function useNotification() {
  const notificationsStore = useNotificationsStore();

  return {
    error: (title: string, message: string, durationMs?: number) =>
      notificationsStore.pushError(title, message, durationMs),
    info: (title: string, message: string, durationMs?: number) =>
      notificationsStore.pushInfo(title, message, durationMs),
    success: (title: string, message: string, durationMs?: number) =>
      notificationsStore.pushSuccess(title, message, durationMs),
    warning: (title: string, message: string, durationMs?: number) =>
      notificationsStore.pushWarning(title, message, durationMs),
  };
}
