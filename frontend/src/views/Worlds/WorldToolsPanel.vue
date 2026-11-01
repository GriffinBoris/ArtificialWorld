<template>
  <section
    class="tools-panel game-panel"
    :aria-label="title"
  >
    <header class="tools-header">
      <div>
        <span class="eyebrow">{{
          kind === "people" ? "THE NEIGHBORHOOD" : kind === "journal" ? "A WORLD WITH A STORY" : "BEHIND THE SCENES"
        }}</span>
        <h2>{{ title }}</h2>
      </div>
      <GameButton
        label="Close panel"
        :icon="X"
        icon-only
        @click="emit('close')"
      />
    </header>
    <div class="tools-content">
      <template v-if="kind === 'people'"
        ><p class="panel-intro">Everyone has a little story. Pick someone to follow along.</p>
        <button
          v-for="agent in store.displayState?.inhabitants"
          :key="agent.id"
          class="neighbor-row"
          type="button"
          :aria-label="`Inspect ${agent.name}`"
          @click="
            store.selectInhabitant(agent.id);
            emit('close');
          "
        >
          <span
            class="neighbor-portrait"
            :style="{ background: inhabitantColor(agent.id) }"
            ><img
              :src="assetUrl('villager-portrait.png')"
              alt="" /></span
          ><span
            ><strong>{{ agent.name }}</strong
            ><small>{{ activityLabel(agent, store.world?.status === "running") }}</small></span
          ><ChevronRight :size="16" /></button
      ></template>
      <template v-else-if="kind === 'journal'"
        ><p class="panel-intro">The small things that make a world.</p>
        <div
          class="journal-list"
          data-testid="world-events"
        >
          <article
            v-for="event in moments"
            :key="event.id"
            class="life-event"
          >
            <span class="timeline-dot" />
            <div>
              <time>{{ formatWorldTime(event.tick) }}</time>
              <p>{{ describeWorldEvent(event, store.displayState) }}</p>
            </div>
          </article>
          <p
            v-if="!moments.length"
            class="profile-empty"
          >
            The story is just beginning.
          </p>
        </div></template
      >
      <template v-else-if="kind === 'object' && store.selectedEntity"
        ><div class="object-card">
          <span class="object-symbol">{{ store.selectedEntity.material === "wood" ? "♧" : "◇" }}</span>
          <h3>{{ store.selectedEntity.name }}</h3>
          <p>{{ store.selectedEntity.material }} · {{ store.selectedEntity.kind }}</p>
        </div>
        <div class="life-stats">
          <div>
            <span>Mass</span><strong>{{ store.selectedEntity.mass.toFixed(2) }} kg</strong>
          </div>
          <div>
            <span>Condition</span><strong>{{ Math.round(store.selectedEntity.condition) }}%</strong>
          </div>
        </div>
        <div
          v-if="store.selectedEntity.resource"
          class="resource-card"
        >
          <strong>{{
            store.selectedEntity.kind === "seed"
              ? "Plantable seeds or a cutting"
              : store.selectedEntity.resource.supply === "infinite"
                ? "∞ Inexhaustible source"
                : store.selectedEntity.resource.growthSeconds
                  ? "A living, renewable resource"
                  : "A finite supply of material"
          }}</strong>
          <p v-if="store.selectedEntity.kind === 'seed'">
            Plant in dry soil within reach. Seeds and cuttings start growing once rooted.
          </p>
          <p v-else-if="store.selectedEntity.resource.growthSeconds">
            {{ Math.round((store.selectedEntity.mass / store.selectedEntity.resource.capacity) * 100) }}% grown · about
            {{ (store.selectedEntity.resource.growthSeconds / 3600).toFixed(1) }} simulated hours to regrow.
          </p>
          <p v-else-if="store.selectedEntity.resource.supply === 'infinite'">
            Gathering supplies new stone without exhausting this quarry face.
          </p>
          <p v-else>Gather its material, then reuse it by shaping and building.</p>
          <p v-if="selectedArea">
            {{ selectedArea.name }} naturally reseeds about every
            {{ (selectedArea.renewalSeconds / 3600).toFixed(1) }} simulated hours when there is space.
          </p>
          <p v-if="store.selectedEntity.material === 'wood' && store.selectedEntity.kind === 'resource'">
            Can be felled into a log. Roots regrow; uprooting clears the spot.
          </p>
        </div>
        <WorldRecordInspector
          v-if="store.world"
          :key="store.selectedEntity.id"
          :world-id="store.world.id"
          :entity-id="store.selectedEntity.id"
          :replay-tick="store.replayTick"
      /></template>
      <template v-else-if="store.world"
        ><nav class="settings-tabs">
          <button
            v-for="tab in ['world', 'agents', 'records']"
            :key="tab"
            type="button"
            :class="{ active: settingsTab === tab }"
            @click="settingsTab = tab"
          >
            {{ tab }}
          </button>
        </nav>
        <p class="panel-intro">
          {{
            store.world.status === "running"
              ? "Pause the world to change its rules or place things."
              : "A quiet moment to make a few changes."
          }}
        </p>
        <GameButton
          v-if="store.world.status === 'running'"
          label="Pause world"
          :icon="Pause"
          @click="store.toggleRun()"
        /><WorldEditor
          v-if="settingsTab === 'world'"
          :world-id="store.world.id"
          :selected-entity="store.selectedEntity"
          :disabled="locked"
          @updated="store.acceptWorldUpdate"
        /><WorldAgentControls
          v-else-if="settingsTab === 'agents'"
          :world="store.world"
          :selected-id="store.selectedId"
          :disabled="locked"
          @updated="store.acceptWorldUpdate"
        /><WorldRecordInspector
          v-else
          :world-id="store.world.id"
          :entity-id="store.selectedId"
          :replay-tick="store.replayTick"
        />
        <p class="settings-footnote">
          {{ store.world.state.inhabitants.filter((agent) => agent.driver === "pydantic").length }} AI inhabitants ·
          {{ store.world.configuration.allowLiveModels ? "Model calls allowed in this world" : "Model calls off" }}
        </p></template
      >
    </div>
  </section>
</template>
<script setup lang="ts">
  import {
    activityLabel,
    assetUrl,
    describeWorldEvent,
    formatWorldTime,
    inhabitantColor,
  } from "@/features/worlds/presentation";
  import GameButton from "@/views/Worlds/GameButton.vue";
  import WorldAgentControls from "@/views/Worlds/WorldAgentControls.vue";
  import WorldEditor from "@/views/Worlds/WorldEditor.vue";
  import WorldRecordInspector from "@/views/Worlds/WorldRecordInspector.vue";
  import { useWorldsStore } from "@/views/Worlds/worldsStore";
  import { ChevronRight, Pause, X } from "@lucide/vue";
  import { computed, ref } from "vue";
  const props = defineProps<{ kind: "people" | "journal" | "settings" | "object" }>();
  const emit = defineEmits<{ close: [] }>();
  const store = useWorldsStore();
  const settingsTab = ref("world");
  const title = computed(
    () =>
      ({ people: "Little lives", journal: "Little moments", settings: "World settings", object: "A closer look" })[
        props.kind
      ]
  );
  const locked = computed(() => store.busy || store.world?.status !== "paused" || store.replayTick !== null);
  const moments = computed(() =>
    store.visibleEvents.filter(
      (event) => !["activity.started", "decision.observed", "world.advanced"].includes(event.kind)
    )
  );
  const selectedArea = computed(() =>
    store.displayState?.resourceAreas?.find((area) => area.id === store.selectedEntity?.resource?.areaId)
  );
</script>
