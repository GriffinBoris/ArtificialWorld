import { worldsApi } from "@/features/worlds/api";
import type { RecordedMotion, WorldDetail, WorldState } from "@/types/worlds/WorldInterface";
import { ref, shallowRef } from "vue";

export function useLiveWorldMotion() {
  const state = shallowRef<WorldState | null>(null);
  const playing = ref(false);
  let latest: WorldDetail | null = null;
  let cursor = 0;
  let generation = 0;
  let frames: RecordedMotion["frames"] = [];
  let timer: ReturnType<typeof setTimeout> | undefined;
  let nextAt = 0;
  let stepping = false;

  function reset(world: WorldDetail | null) {
    generation++;
    clearTimeout(timer);
    timer = undefined;
    frames = [];
    playing.value = false;
    stepping = false;
    latest = world;
    cursor = world?.tick ?? 0;
    state.value = world?.state ?? null;
    nextAt = performance.now();
  }

  function playNext() {
    const frame = frames.shift();

    if (!frame) {
      playing.value = false;
      stepping = false;

      if (latest && state.value?.tick === latest.tick) state.value = latest.state;

      return;
    }

    playing.value = true;
    nextAt += ((frame.tick - state.value!.tick) / frame.state.config.physicsHz) * 1000;
    timer = setTimeout(
      () => {
        timer = undefined;
        let current = frame;
        const now = performance.now();

        while (frames.length) {
          const next = frames[0];
          const delay = ((next.tick - current.tick) / next.state.config.physicsHz) * 1000;

          if (nextAt + delay > now) break;

          nextAt += delay;
          current = frames.shift()!;
        }

        state.value = current.state;
        playNext();
      },
      Math.max(0, nextAt - performance.now())
    );
  }

  async function update(world: WorldDetail, animateStep = false) {
    if (
      latest?.id !== world.id ||
      (world.status !== "running" && !animateStep && !stepping) ||
      world.tick < state.value!.tick
    ) {
      reset(world);

      return;
    }

    if (animateStep) stepping = true;

    latest = world;

    if (world.tick <= cursor) {
      if (!timer && !frames.length) state.value = world.state;

      return;
    }

    const current = generation;
    const recording = await worldsApi.motion(world.id, cursor);

    if (current !== generation) return;

    cursor = Math.min(world.tick, recording.untilTick);
    const next = recording.frames.filter((frame) => frame.tick <= world.tick);

    if (!next.length) {
      reset(world);

      return;
    }

    frames.push(...next);

    if (!timer) {
      if (performance.now() - nextAt > 300) nextAt = performance.now();

      playNext();
    }
  }

  return { state, playing, reset, update };
}
