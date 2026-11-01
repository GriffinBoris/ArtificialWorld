<template>
  <details
    class="border-line rounded-md border p-4"
    @toggle="onToggle"
  >
    <summary class="cursor-pointer text-sm font-medium">Selected object's records</summary>
    <p
      v-if="replayTick !== null"
      class="text-secondary mt-4 text-xs"
    >
      Records at the selected replay time. Later versions and memories are hidden.
    </p>
    <p
      v-if="loading"
      class="text-secondary mt-4 text-xs"
    >
      Loading records…
    </p>
    <p
      v-if="error"
      role="alert"
      class="text-error mt-4 text-xs"
    >
      {{ error }}
    </p>
    <div
      v-if="inspection"
      class="mt-4 space-y-5 text-sm"
    >
      <article
        v-for="artifact in inspection.artifacts"
        :key="artifact.id"
      >
        <h3 class="font-medium">{{ artifact.title }} · {{ artifact.kind }}</h3>
        <details
          v-for="version in artifact.versions"
          :key="version.version"
          class="mt-2"
        >
          <summary class="text-secondary cursor-pointer text-xs">
            Version {{ version.version }} · tick {{ version.tick }}
          </summary>
          <pre class="mt-2 max-h-72 overflow-auto text-xs break-words whitespace-pre-wrap">{{ version.content }}</pre>
        </details>
      </article>
      <section v-if="inspection.memories.length">
        <h3 class="font-medium">Personal memories</h3>
        <p
          v-for="(memory, index) in inspection.memories"
          :key="index"
          class="text-secondary mt-2 text-xs whitespace-pre-wrap"
        >
          {{ memory }}
        </p>
      </section>
      <details
        v-for="decision in inspection.decisions"
        :key="decision.id"
      >
        <summary class="cursor-pointer text-xs">Decision at tick {{ decision.tick }} · {{ decision.status }}</summary>
        <pre class="text-secondary mt-2 max-h-96 overflow-auto text-xs break-words whitespace-pre-wrap">{{
          JSON.stringify(decision, null, 2)
        }}</pre>
      </details>
      <pre
        v-for="program in inspection.programs"
        :key="program.artifactVersionId"
        class="text-secondary max-h-72 overflow-auto text-xs whitespace-pre-wrap"
        >{{ JSON.stringify(program, null, 2) }}</pre
      >
      <p
        v-if="
          !inspection.artifacts.length &&
          !inspection.memories.length &&
          !inspection.decisions.length &&
          !inspection.programs.length
        "
        class="text-secondary text-xs"
      >
        No documents, memories, decisions, or programs recorded for this object yet.
      </p>
    </div>
  </details>
</template>

<script setup lang="ts">
  import { worldsApi } from "@/features/worlds/api";
  import type { EntityInspection } from "@/types/worlds/WorldInterface";
  import { usePolling } from "@/composables/usePolling";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { onBeforeUnmount, ref, watch } from "vue";

  const props = defineProps<{ worldId: string; entityId: string | null; replayTick: number | null }>();
  const inspection = ref<EntityInspection | null>(null);
  const open = ref(false);
  const error = ref("");
  const loading = ref(false);
  let generation = 0;
  let disposed = false;
  let seekTimer: ReturnType<typeof setTimeout> | undefined;

  async function load() {
    if (!props.entityId || !open.value || loading.value) return;

    const current = generation;
    loading.value = true;

    try {
      const result = await worldsApi.inspect(props.worldId, props.entityId, props.replayTick);

      if (!disposed && current === generation) {
        inspection.value = result;
        error.value = "";
      }
    } catch (failure) {
      if (!disposed && current === generation)
        error.value = getFirstApiErrorMessage(failure, "Could not load this object's records.");
    } finally {
      loading.value = false;
    }
  }
  const polling = usePolling(load, () => disposed, 2000, { autoStart: false });
  watch(
    () => [props.worldId, props.entityId],
    () => {
      generation++;
      inspection.value = null;
      error.value = "";
      void load();
    }
  );
  watch(
    () => props.replayTick,
    () => {
      generation++;
      inspection.value = null;
      clearTimeout(seekTimer);
      seekTimer = setTimeout(load, 200);
    }
  );
  function onToggle(event: Event) {
    open.value = (event.target as HTMLDetailsElement).open;

    if (open.value) polling.startPolling();
    else polling.stopPolling();
  }
  onBeforeUnmount(() => {
    clearTimeout(seekTimer);
    disposed = true;
    generation++;
  });
</script>
