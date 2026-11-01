import { type Ref, onBeforeUnmount, ref } from "vue";

export interface UsePollingOptions {
  autoStart?: boolean;
  immediate?: boolean;
}

export interface UsePollingReturn {
  isPolling: Readonly<Ref<boolean>>;
  startPolling: () => void;
  stopPolling: () => void;
}

export function usePolling(
  callback: () => void | Promise<void>,
  shouldStop: () => boolean,
  intervalMs: number,
  options: UsePollingOptions = {}
): UsePollingReturn {
  const autoStart = options.autoStart ?? true;
  const immediate = options.immediate ?? true;
  const isPolling = ref(false);
  let intervalId: ReturnType<typeof window.setInterval> | null = null;

  function stopPolling() {
    if (intervalId !== null) {
      window.clearInterval(intervalId);
      intervalId = null;
    }

    isPolling.value = false;
  }

  function runPollingCallback() {
    if (shouldStop()) {
      stopPolling();

      return;
    }

    void callback();
  }

  function startPolling() {
    if (intervalId !== null) {
      return;
    }

    if (shouldStop()) {
      stopPolling();

      return;
    }

    isPolling.value = true;

    if (immediate) {
      runPollingCallback();

      if (shouldStop()) {
        stopPolling();

        return;
      }
    }

    intervalId = window.setInterval(runPollingCallback, intervalMs);
  }

  onBeforeUnmount(stopPolling);

  if (autoStart) {
    startPolling();
  }

  return {
    isPolling,
    startPolling,
    stopPolling,
  };
}
