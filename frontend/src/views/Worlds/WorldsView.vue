<template>
  <main
    class="world-game"
    aria-label="Little World spectator"
  >
    <WorldScene
      v-if="store.displayState && store.terrain && store.world"
      :key="store.world.id"
      ref="scene"
      :state="store.displayState"
      :terrain="store.terrain"
      :selected-id="store.selectedId"
      :messages="store.displayMessages"
      :replay="store.replayTick !== null"
      :running="store.world.status === 'running'"
      :motion-playing="store.motionPlaying"
      :follow-id="store.followId"
      :interactive="!store.showMenu && !store.showCreate && !store.profileExpanded"
      @select="selectEntity"
      @conversation="meet($event, 'chat', true)"
      @thinking="meet($event, 'mind', true)"
    />
    <div
      v-else
      class="world-loading"
    >
      <span class="loading-flower">✿</span>
      <p>{{ store.error ? "Our little world needs a moment." : "Finding a little place in the world…" }}</p>
      <GameButton
        v-if="store.error"
        label="Try again"
        :icon="RotateCcw"
        @click="store.initialize()"
      />
    </div>
    <header class="game-topbar">
      <GameButton
        label="Menu"
        :icon="Menu"
        :disabled="store.busy || store.loading"
        test-id="world-menu"
        @click="store.openMenu()"
      />
      <div class="world-brand">
        <span class="brand-sprout"
          ><Sprout
            :size="27"
            stroke-width="2"
        /></span>
        <div>
          <h1>little world<span>✦</span></h1>
          <p>A place for little lives.</p>
        </div>
      </div>
      <div
        v-if="store.world"
        class="world-name-pill"
      >
        <span class="world-name-dot" /><select
          :value="store.world.id"
          aria-label="Selected world"
          @change="store.selectWorld(($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="world in store.worlds"
            :key="world.id"
            :value="world.id"
          >
            {{ world.name }}
          </option></select
        ><ChevronDown :size="13" />
      </div>
      <div class="topbar-space" />
      <div
        v-if="store.world"
        class="day-pill"
      >
        <Sun :size="20" />
        <div>
          <strong>Day {{ Math.floor((store.displayState?.tick ?? 0) / 60 / 86400) + 1 }}</strong
          ><small>{{ formatWorldTime(store.displayState?.tick ?? 0) }}</small>
        </div>
      </div>
      <div
        v-if="store.world"
        class="saved-pill"
      >
        <span class="saved-sparkle">✧</span>
        <div><strong>Every little moment</strong><small>Saved as life unfolds</small></div>
      </div>
      <GameButton
        label="World settings"
        :icon="Settings2"
        icon-only
        :active="panel === 'settings'"
        @click="togglePanel('settings')"
      />
    </header>

    <nav
      v-if="store.world"
      class="world-rail game-panel"
      aria-label="Spectator tools"
    >
      <GameButton
        label="Return to clearing"
        :icon="Compass"
        icon-only
        @click="scene?.resetView()"
      /><GameButton
        label="Landscape view"
        :icon="Mountain"
        icon-only
        @click="scene?.landscapeView()"
      /><span class="rail-divider" /><GameButton
        label="Inhabitants"
        :icon="Users"
        icon-only
        :active="panel === 'people'"
        test-id="show-inhabitants"
        @click="togglePanel('people')"
      /><GameButton
        label="World history"
        :icon="BookOpen"
        icon-only
        :active="panel === 'journal'"
        test-id="show-history"
        @click="togglePanel('journal')"
      /><GameButton
        label="New world"
        :icon="Plus"
        icon-only
        test-id="new-world"
        @click="store.openCreate()"
      />
    </nav>
    <div
      v-if="store.world"
      class="camera-tools"
    >
      <GameButton
        label="Zoom in"
        :icon="ZoomIn"
        icon-only
        @click="scene?.zoom(0.8)"
      /><GameButton
        label="Zoom out"
        :icon="ZoomOut"
        icon-only
        @click="scene?.zoom(1.25)"
      /><GameButton
        label="Find selected inhabitant"
        :icon="Focus"
        icon-only
        @click="scene?.focusSelected()"
      />
    </div>

    <div
      v-if="store.error || store.world?.error"
      role="alert"
      class="game-error"
    >
      <p>{{ store.error || store.world?.error }}</p>
      <button
        type="button"
        aria-label="Dismiss error"
        @click="
          store.error = '';
          if (store.world) store.world.error = '';
        "
      >
        <X :size="16" />
      </button>
    </div>

    <template v-if="store.world">
      <WorldMinimap @focus="scene?.focusPoint($event)" />
      <div class="world-status">
        <span
          class="status-dot"
          :class="{ paused: store.world.status !== 'running' }"
        /><strong>{{
          store.replayTick !== null
            ? "A moment from the past"
            : store.world.status === "running"
              ? "Life is unfolding"
              : "A quiet little moment"
        }}</strong
        ><span>{{ store.livingCount }} inhabitants</span>
      </div>
      <div class="spectator-hint">
        <MousePointer2 :size="13" /><span>Drag to explore · scroll to zoom · click someone to meet them</span>
      </div>
      <div
        class="game-controls game-panel"
        :class="{ 'is-replay': store.replayTick !== null }"
      >
        <span class="control-label"
          ><span class="control-flower">✿</span
          >{{ store.replayTick === null ? "Let life unfold" : "World memories" }}</span
        >
        <span class="control-divider" />
        <GameButton
          v-if="store.replayTick === null"
          :label="store.world.status === 'running' ? 'Pause' : 'Play'"
          :icon="store.world.status === 'running' ? Pause : Play"
          primary
          :disabled="store.busy"
          test-id="toggle-world"
          @click="store.toggleRun()"
        />
        <GameButton
          v-else
          :label="store.playing ? 'Pause replay' : 'Play recording'"
          :icon="store.playing ? Pause : Play"
          primary
          :disabled="store.replayTick >= store.world.tick && !store.playing"
          test-id="play-recording"
          @click="store.togglePlayback()"
        />
        <GameButton
          label="Step 5 s"
          :icon="StepForward"
          icon-only
          :disabled="store.busy || store.world.status === 'running' || store.replayTick !== null"
          test-id="step-world"
          @click="store.stepWorld()"
        />
        <span class="control-divider" /><GameButton
          :label="store.replayTick === null ? 'Replay' : 'Back to live'"
          :icon="store.replayTick === null ? History : Radio"
          :disabled="store.busy || store.world.tick === 0"
          test-id="toggle-replay"
          @click="store.toggleReplay()"
        />
      </div>
      <div
        v-if="store.replayTick !== null"
        class="replay-strip game-panel"
      >
        <span>Replay · read only</span
        ><input
          :value="store.replayTick"
          type="range"
          min="0"
          :max="store.world.tick"
          step="1"
          aria-label="Replay time"
          @input="store.seekReplay(Number(($event.target as HTMLInputElement).value))"
        /><time>{{ formatWorldTime(store.replayTick) }}</time>
      </div>
      <Transition
        name="game-panel"
        :css="!store.profileExpanded"
        ><WorldToolsPanel
          v-if="panel"
          :key="panel"
          :kind="panel"
          @close="panel = null" /><WorldCharacterPanel
          v-else-if="store.selectedInhabitant && !store.profileExpanded"
          :key="store.selectedId!"
          @focus="scene?.focusSelected()"
          @settings="panel = 'settings'"
      /></Transition>
      <div
        class="little-portraits"
        aria-label="Meet the inhabitants"
      >
        <button
          v-for="agent in store.displayState?.inhabitants.slice(0, 10)"
          :key="agent.id"
          :aria-label="`Inspect ${agent.name}`"
          :title="agent.name"
          :class="{ selected: store.selectedId === agent.id, deceased: !agent.alive }"
          :style="{ '--person-color': inhabitantColor(agent.id) }"
          type="button"
          @click="meet(agent.id)"
        >
          <img
            :src="assetUrl('villager-portrait.png')"
            alt=""
          /><span>{{ agent.name.split(" ").at(-1) }}</span></button
        ><button
          v-if="store.displayState && store.displayState.inhabitants.length > 10"
          aria-label="See all inhabitants"
          type="button"
          @click="panel = 'people'"
        >
          +{{ store.displayState.inhabitants.length - 10 }}
        </button>
      </div>
    </template>
    <GameDialog
      v-if="store.profileExpanded && store.selectedInhabitant"
      label="Inhabitant details"
      fullscreen
      @close="store.profileExpanded = false"
    >
      <WorldCharacterPanel
        expanded
        @settings="
          store.profileExpanded = false;
          panel = 'settings';
        "
      />
    </GameDialog>
    <WorldMenu v-if="store.showMenu && !store.showCreate" />
    <WorldCreateDialog v-if="store.showCreate" />
  </main>
</template>

<script setup lang="ts">
  import { assetUrl, formatWorldTime, inhabitantColor } from "@/features/worlds/presentation";
  import WorldScene from "@/features/worlds/WorldScene.vue";
  import GameButton from "@/views/Worlds/GameButton.vue";
  import GameDialog from "@/views/Worlds/GameDialog.vue";
  import WorldCharacterPanel from "@/views/Worlds/WorldCharacterPanel.vue";
  import WorldCreateDialog from "@/views/Worlds/WorldCreateDialog.vue";
  import WorldMenu from "@/views/Worlds/WorldMenu.vue";
  import WorldMinimap from "@/views/Worlds/WorldMinimap.vue";
  import WorldToolsPanel from "@/views/Worlds/WorldToolsPanel.vue";
  import { useWorldsStore } from "@/views/Worlds/worldsStore";
  import {
    BookOpen,
    ChevronDown,
    Compass,
    Focus,
    History,
    Menu,
    Mountain,
    MousePointer2,
    Pause,
    Play,
    Plus,
    Radio,
    RotateCcw,
    Settings2,
    Sprout,
    StepForward,
    Sun,
    Users,
    X,
    ZoomIn,
    ZoomOut,
  } from "@lucide/vue";
  import { onBeforeUnmount, onMounted, ref } from "vue";
  import "@/views/Worlds/game.css";
  const store = useWorldsStore();
  const scene = ref<InstanceType<typeof WorldScene>>();
  const panel = ref<"people" | "journal" | "settings" | "object" | null>(null);
  function togglePanel(kind: "people" | "journal" | "settings") {
    panel.value = panel.value === kind ? null : kind;
  }
  function selectEntity(id: string) {
    store.selectedId = id;
    panel.value = store.displayState?.inhabitants.some((agent) => agent.id === id) ? null : "object";
  }
  function meet(id: string, tab: "chat" | "memories" | "history" | "mind" = "chat", expanded = false) {
    store.selectInhabitant(id, tab);
    store.profileExpanded = expanded;
    panel.value = null;
  }
  function keyboard(event: KeyboardEvent) {
    if (event.defaultPrevented || store.showMenu || store.showCreate || store.profileExpanded) return;

    if (event.key === "Escape") {
      if (panel.value || store.selectedId) {
        panel.value = null;
        store.selectedId = null;
        store.followId = null;
      } else void store.openMenu();

      return;
    }

    if (
      event.target instanceof HTMLElement &&
      event.target.closest(
        "input, textarea, select, button, dialog, [role='combobox'], [role='listbox'], [role='option'], [contenteditable]"
      )
    )
      return;

    if (event.code === "Space" && !store.busy && store.replayTick === null && !store.showCreate) {
      event.preventDefault();
      void store.toggleRun();
    }

    if (event.key.toLowerCase() === "f") scene.value?.focusSelected();
  }
  onMounted(() => {
    void store.initialize();
    window.addEventListener("keydown", keyboard);
  });
  onBeforeUnmount(() => {
    window.removeEventListener("keydown", keyboard);
    store.dispose();
  });
</script>
