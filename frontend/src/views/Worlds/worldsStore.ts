import { usePolling } from "@/composables/usePolling";
import { worldsApi } from "@/features/worlds/api";
import type {
  Terrain,
  WorldDetail,
  WorldEvent,
  WorldMessage,
  WorldState,
  WorldSummary,
} from "@/types/worlds/WorldInterface";
import { getFirstApiErrorMessage } from "@/utils/errorHandling";
import { useLiveWorldMotion } from "@/views/Worlds/useLiveWorldMotion";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useWorldsStore = defineStore("worlds", () => {
  const worlds = ref<WorldSummary[]>([]);
  const world = ref<WorldDetail | null>(null);
  const terrain = ref<Terrain | null>(null);
  const events = ref<WorldEvent[]>([]);
  const messages = ref<WorldMessage[]>([]);
  const replayMessages = ref<WorldMessage[]>([]);
  const profileTab = ref<"chat" | "memories" | "history" | "mind">("chat");
  const profileExpanded = ref(false);
  const followId = ref<string | null>(null);
  const selectedId = ref<string | null>(null);
  const loading = ref(true);
  const busy = ref(false);
  const error = ref("");
  const showCreate = ref(false);
  const showMenu = ref(false);
  const newName = ref("Little beginnings");
  const newSeed = ref(42);
  const newPopulation = ref(6);
  const replayTick = ref<number | null>(null);
  const replayState = ref<WorldState | null>(null);
  const liveMotion = useLiveWorldMotion();
  const displayState = computed(() => (replayTick.value === null ? liveMotion.state.value : replayState.value));
  const livingCount = computed(() => displayState.value?.inhabitants.filter((agent) => agent.alive).length ?? 0);
  const selectedEntity = computed(() => displayState.value?.entities.find((entity) => entity.id === selectedId.value));
  const selectedInhabitant = computed(() =>
    displayState.value?.inhabitants.find((agent) => agent.id === selectedId.value)
  );
  const visibleEvents = computed(() =>
    events.value
      .filter((event) => event.tick <= (displayState.value?.tick ?? 0))
      .slice(-50)
      .reverse()
  );
  const playing = ref(false);
  let playbackTimer: ReturnType<typeof setTimeout> | undefined;
  let seekTimer: ReturnType<typeof setTimeout> | undefined;
  let disposed = false;
  let polling = false;
  let generation = 0;
  let seekGeneration = 0;
  const pollingControl = usePolling(refresh, () => disposed, 1000, { autoStart: false });

  async function selectWorld(id: string) {
    profileExpanded.value = false;
    followId.value = null;
    stopPlayback();
    const current = ++generation;
    seekGeneration++;
    replayTick.value = null;
    replayState.value = null;
    loading.value = true;
    error.value = "";

    try {
      const [detail, landscape, history, conversation] = await Promise.all([
        worldsApi.detail(id),
        worldsApi.terrain(id),
        worldsApi.events(id, 0),
        worldsApi.messages(id),
      ]);

      if (disposed || current !== generation) return false;

      world.value = detail;
      liveMotion.reset(detail);
      terrain.value = landscape;
      events.value = history;
      messages.value = conversation;
      selectedId.value = null;

      return true;
    } catch (failure) {
      if (!disposed && current === generation)
        error.value = getFirstApiErrorMessage(failure, "Could not open this world. Try again.");

      return false;
    } finally {
      if (!disposed && current === generation) loading.value = false;
    }
  }

  async function refresh() {
    if (polling || busy.value || !world.value || disposed || loading.value) return;

    polling = true;
    const current = generation;
    const id = world.value.id;

    try {
      const [detail, nextEvents, conversation] = await Promise.all([
        worldsApi.detail(id),
        worldsApi.events(id, events.value.at(-1)?.sequence ?? 0),
        worldsApi.messages(id),
      ]);

      if (disposed || current !== generation) return;

      const accepted = world.value && detail.revision >= world.value.revision;

      if (accepted) world.value = detail;

      events.value = [...events.value, ...nextEvents].slice(-500);
      messages.value = conversation;

      if (accepted && replayTick.value === null) await liveMotion.update(detail);
    } catch (failure) {
      if (!disposed && current === generation)
        error.value = getFirstApiErrorMessage(failure, "Connection interrupted. Reconnecting to the world…");
    } finally {
      polling = false;
    }
  }

  async function mutate(operation: () => Promise<void>) {
    busy.value = true;
    error.value = "";

    try {
      await operation();
    } catch (failure) {
      if (!disposed) error.value = getFirstApiErrorMessage(failure, "The action could not be completed.");
    } finally {
      if (!disposed) busy.value = false;
    }
  }

  async function createWorld() {
    await mutate(async () => {
      const created = await worldsApi.create(newName.value, newSeed.value, newPopulation.value);

      if (disposed) return;

      worlds.value.unshift(created);

      if (await selectWorld(created.id)) {
        showCreate.value = false;
        showMenu.value = false;
      }
    });
  }

  async function openMenu() {
    if (busy.value) return;

    showMenu.value = true;
    profileExpanded.value = false;
    selectedId.value = null;
    followId.value = null;
    stopPlayback();
    const current = generation;
    await mutate(async () => {
      const id = world.value?.id;

      if (world.value?.status === "running" && id) {
        await worldsApi.status(id, "paused");
        const detail = await worldsApi.detail(id);

        if (!disposed && world.value?.id === id) acceptWorldUpdate(detail);
      }

      const list = await worldsApi.list();

      if (!disposed && current === generation) worlds.value = list;
    });
  }

  async function openSavedWorld(id: string) {
    if (busy.value) return;

    if (world.value?.id === id || (await selectWorld(id))) showMenu.value = false;
  }

  function openCreate() {
    error.value = "";
    showCreate.value = true;
  }

  async function deleteWorld(id: string) {
    if (busy.value || loading.value) return;

    generation++;
    await mutate(async () => {
      await worldsApi.status(id, "paused");
      await worldsApi.delete(id);

      if (disposed) return;

      worlds.value = worlds.value.filter((saved) => saved.id !== id);

      if (world.value?.id !== id) return;

      stopPlayback();
      seekGeneration++;
      clearTimeout(seekTimer);
      liveMotion.reset(null);
      world.value = null;
      terrain.value = null;
      selectedId.value = null;
      followId.value = null;
      profileExpanded.value = false;
      events.value = [];
      messages.value = [];
      replayMessages.value = [];
      replayTick.value = null;
      replayState.value = null;

      if (worlds.value[0]) await selectWorld(worlds.value[0].id);
    });
  }

  async function toggleRun() {
    if (!world.value) return;

    const id = world.value.id;
    await mutate(async () => {
      await worldsApi.status(id, world.value?.status === "running" ? "paused" : "running");
      const detail = await worldsApi.detail(id);

      if (!disposed && world.value?.id === id) acceptWorldUpdate(detail);
    });
  }

  async function stepWorld() {
    if (!world.value) return;

    const id = world.value.id;
    await mutate(async () => {
      const detail = await worldsApi.step(id);

      if (!disposed && world.value?.id === id) {
        world.value = detail;
        await liveMotion.update(detail, true);
      }
    });
    await refresh();
  }

  function acceptWorldUpdate(updated: WorldDetail) {
    if (world.value?.id === updated.id && updated.revision >= world.value.revision) {
      world.value = updated;
      liveMotion.reset(updated);
    }
  }

  function toggleReplay() {
    stopPlayback();
    liveMotion.reset(world.value);

    if (replayTick.value !== null) {
      seekGeneration++;
      replayTick.value = null;
      replayState.value = null;

      return;
    }

    replayState.value = world.value?.state ?? null;
    seekReplay(0);
  }

  function seekReplay(tick: number) {
    stopPlayback();

    if (!world.value) return;

    replayTick.value = tick;
    const current = ++seekGeneration;
    const id = world.value.id;
    clearTimeout(seekTimer);
    seekTimer = setTimeout(async () => {
      try {
        const [result, conversation] = await Promise.all([worldsApi.replay(id, tick), worldsApi.messages(id, tick)]);

        if (!disposed && current === seekGeneration && world.value?.id === id) {
          replayState.value = result.state;
          replayMessages.value = conversation;
        }
      } catch (failure) {
        if (!disposed && current === seekGeneration)
          error.value = getFirstApiErrorMessage(failure, "Could not read this recording.");
      }
    }, 100);
  }

  function stopPlayback() {
    playing.value = false;
    clearTimeout(playbackTimer);
  }

  async function togglePlayback() {
    if (playing.value) {
      stopPlayback();

      return;
    }

    if (!world.value || replayTick.value === null) return;

    clearTimeout(seekTimer);
    playing.value = true;
    const current = ++seekGeneration;
    const id = world.value.id;
    let cursor = replayTick.value;

    async function readNext() {
      try {
        const recording = await worldsApi.motion(id, cursor);

        if (disposed || !playing.value || current !== seekGeneration || world.value?.id !== id) return;

        replayMessages.value = await worldsApi.messages(id, recording.untilTick);

        if (disposed || !playing.value || current !== seekGeneration) return;

        let index = 0;

        function showNext() {
          if (disposed || !playing.value || current !== seekGeneration) return;

          const frame = recording.frames[index++];

          if (!frame) {
            cursor = recording.untilTick;

            if (cursor >= (world.value?.tick ?? cursor)) {
              stopPlayback();

              return;
            }

            void readNext();

            return;
          }

          replayState.value = frame.state;
          replayTick.value = frame.tick;
          const delay = Math.max(1, ((frame.tick - cursor) / 60) * 1000);
          cursor = frame.tick;
          playbackTimer = setTimeout(showNext, delay);
        }

        showNext();
      } catch (failure) {
        if (!disposed && current === seekGeneration) {
          stopPlayback();
          error.value = getFirstApiErrorMessage(failure, "Could not play this recording.");
        }
      }
    }

    await readNext();
  }

  async function initialize() {
    disposed = false;
    loading.value = true;

    try {
      const list = await worldsApi.list();

      if (disposed) return;

      worlds.value = list;

      if (list[0]) await selectWorld(list[0].id);
      else await createWorld();
    } catch (failure) {
      if (!disposed) error.value = getFirstApiErrorMessage(failure, "Could not load your worlds.");
    } finally {
      if (!disposed) loading.value = false;
    }

    if (!disposed) pollingControl.startPolling();
  }

  function dispose() {
    disposed = true;
    generation++;
    seekGeneration++;
    stopPlayback();
    clearTimeout(seekTimer);
    liveMotion.reset(null);
    pollingControl.stopPolling();
  }

  const displayMessages = computed(() =>
    (replayTick.value === null ? messages.value : replayMessages.value).filter(
      (message) => message.tick <= (displayState.value?.tick ?? 0)
    )
  );

  function selectInhabitant(id: string, tab: "chat" | "memories" | "history" | "mind" = "chat") {
    profileExpanded.value = false;
    selectedId.value = id;
    profileTab.value = tab;
  }

  return {
    followId,
    worlds,
    world,
    terrain,
    events,
    selectedId,
    selectedEntity,
    selectedInhabitant,
    profileTab,
    profileExpanded,
    messages,
    displayMessages,
    loading,
    busy,
    error,
    showCreate,
    showMenu,
    newName,
    newSeed,
    newPopulation,
    replayTick,
    replayState,
    displayState,
    livingCount,
    visibleEvents,
    playing,
    motionPlaying: liveMotion.playing,
    initialize,
    dispose,
    refresh,
    selectWorld,
    selectInhabitant,
    createWorld,
    deleteWorld,
    openMenu,
    openSavedWorld,
    openCreate,
    toggleRun,
    stepWorld,
    acceptWorldUpdate,
    toggleReplay,
    seekReplay,
    stopPlayback,
    togglePlayback,
  };
});
