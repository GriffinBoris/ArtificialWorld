<template>
  <details
    class="border-line rounded-md border p-4"
    @toggle="onToggle"
  >
    <summary class="cursor-pointer text-sm font-medium">Agent settings</summary>
    <div
      v-if="open"
      class="mt-4 space-y-4"
    >
      <p class="text-secondary text-xs">
        Configure inhabitants while paused. Up to {{ availability?.thinkingSlots ?? 4 }} inhabitants can think at once.
        The world keeps moving while they think.
      </p>
      <p
        v-if="availability"
        class="text-secondary text-xs"
      >
        {{ availability.provider === "opencode-go" ? "OpenCode Go" : "ChatGPT" }}:
        {{ availability.subscriptionAuthorized ? "configured" : "not configured" }} · Server model access:
        {{ availability.serverEnabled ? "enabled" : "off" }}
      </p>
      <p
        v-if="availability && !availability.subscriptionAuthorized"
        class="text-secondary text-xs"
      >
        <template v-if="availability.provider === 'opencode-go'"
          >Connect OpenCode Go in your local OpenCode app, or set <code>OPENCODE_GO_API_KEY</code> before starting the
          server.</template
        >
        <template v-else
          >To authorize your local account, run <code>uv run python backend/manage.py agent_login</code>. This does not
          run inference.</template
        >
      </p>
      <p
        v-if="availability && !availability.serverEnabled"
        class="text-secondary text-xs"
      >
        To allow model calls, restart local development with <code>WORLD_ALLOW_LIVE_AI=1 task local:dev</code>.
      </p>
      <form
        class="flex flex-wrap items-end gap-4"
        @submit.prevent="save"
      >
        <label class="grid min-w-40 gap-2 text-xs"
          >Inhabitants
          <AppSelect
            v-model="scope"
            :options="scopeOptions"
            option-label="label"
            option-value="value"
            input-id="agent-scope"
            aria-label="Inhabitants"
            overlay-class="game-select-overlay"
            :disabled="disabled || saving"
          />
        </label>
        <label class="grid min-w-52 gap-2 text-xs"
          >Driver
          <AppSelect
            v-model="driver"
            :options="driverOptions"
            option-label="label"
            option-value="value"
            input-id="agent-driver"
            aria-label="Driver"
            overlay-class="game-select-overlay"
            :disabled="disabled || saving"
          />
        </label>
        <label
          v-if="driver === 'pydantic'"
          class="grid min-w-52 gap-2 text-xs"
          >Model ID
          <AppInputText
            v-model="modelName"
            input-id="agent-model"
            :disabled="disabled || saving"
            :placeholder="
              availability?.provider === 'opencode-go'
                ? 'For example: glm-5.3-flash'
                : 'Enter a model available to your account'
            "
          />
        </label>
        <label class="flex items-center gap-2 text-xs"
          ><input
            v-model="allowLiveModels"
            type="checkbox"
            :disabled="disabled || saving"
          />Allow model calls in this world</label
        >
        <AppButton
          label="Save agent settings"
          button-type="submit"
          :disabled="disabled || !scope || !driver"
          :loading="saving"
          test-id="save-agent-settings"
        />
      </form>
      <p
        v-if="disabled"
        class="text-secondary text-xs"
      >
        Pause the world and return to live view to change settings.
      </p>
      <p
        v-if="error"
        role="alert"
        class="text-error text-xs"
      >
        {{ error }}
      </p>
    </div>
  </details>
</template>

<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import AppInputText from "@/components/ui/AppInputText.vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import { worldsApi } from "@/features/worlds/api";
  import type { AgentAvailability, WorldDetail } from "@/types/worlds/WorldInterface";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { computed, onBeforeUnmount, ref, watch } from "vue";

  const props = defineProps<{ world: WorldDetail; selectedId: string | null; disabled: boolean }>();
  const emit = defineEmits<{ updated: [world: WorldDetail] }>();
  const open = ref(false);
  const saving = ref(false);
  const error = ref("");
  const availability = ref<AgentAvailability | null>(null);
  const driver = ref<"scripted" | "pydantic" | null>("scripted");
  const modelName = ref("");
  const allowLiveModels = ref(false);
  const scope = ref<"all" | "selected" | null>("all");
  const scopeOptions = computed(() => [
    { label: "All living inhabitants", value: "all" },
    ...(props.world.state.inhabitants.some((agent) => agent.id === props.selectedId && agent.alive)
      ? [{ label: "Selected inhabitant", value: "selected" }]
      : []),
  ]);
  const driverOptions = [
    { label: "Scripted · no model calls", value: "scripted" },
    { label: "Pydantic AI", value: "pydantic" },
  ];
  let generation = 0;

  watch(
    () => props.world.id,
    () => {
      generation++;
      availability.value = null;
      error.value = "";
      allowLiveModels.value = props.world.configuration.allowLiveModels;
      const agent = props.world.state.inhabitants.find((inhabitant) => inhabitant.driver === "pydantic");
      driver.value = agent ? "pydantic" : "scripted";
      modelName.value = agent?.modelName ?? "";
      scope.value = "all";

      if (open.value) void loadAvailability();
    },
    { immediate: true }
  );

  async function loadAvailability() {
    const current = ++generation;

    try {
      const result = await worldsApi.agentAvailability(props.world.id);

      if (current === generation) availability.value = result;
    } catch (failure) {
      if (current === generation) error.value = getFirstApiErrorMessage(failure, "Could not read agent availability.");
    }
  }

  function onToggle(event: Event) {
    open.value = (event.target as HTMLDetailsElement).open;

    if (open.value) void loadAvailability();
  }

  async function save() {
    if (!driver.value || !scope.value) return;

    const current = generation;
    const actorIds = props.world.state.inhabitants
      .filter((agent) => agent.alive && (scope.value === "all" || agent.id === props.selectedId))
      .map((agent) => agent.id);
    saving.value = true;
    error.value = "";

    try {
      const result = await worldsApi.configureAgents(props.world.id, {
        actorIds,
        driver: driver.value,
        modelName: modelName.value,
        allowLiveModels: allowLiveModels.value,
      });

      if (current === generation) emit("updated", result);
    } catch (failure) {
      if (current === generation) error.value = getFirstApiErrorMessage(failure, "Could not save agent settings.");
    } finally {
      saving.value = false;
    }
  }

  onBeforeUnmount(() => {
    generation++;
  });
</script>
