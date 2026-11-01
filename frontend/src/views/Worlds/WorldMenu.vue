<template>
  <GameDialog
    label="World menu"
    wide
    @close="close"
  >
    <section class="world-menu game-panel">
      <header class="world-menu-header">
        <span class="eyebrow">LITTLE WORLD</span
        ><GameButton
          label="Close menu"
          :icon="X"
          icon-only
          :disabled="store.busy || !store.world"
          @click="close"
        />
      </header>
      <div class="world-menu-body">
        <div class="world-menu-intro">
          <img
            :src="assetUrl('villager-portrait.png')"
            alt=""
          />
          <h2>A world of<br />little possibilities.</h2>
          <p>Start a new story, or return to a world you've already begun.</p>
          <GameButton
            label="New world"
            :icon="Plus"
            primary
            :disabled="store.busy || store.loading"
            test-id="menu-new-world"
            @click="store.openCreate()"
          />
          <GameButton
            v-if="store.world"
            label="Back to world"
            :icon="Play"
            :disabled="store.busy || store.loading"
            @click="close"
          />
          <p
            v-if="store.world?.configuration.rulesVersion === 1"
            class="landscape-note"
          >
            {{ store.world.name }} uses an early landscape. A new world includes denser forests, rocks, streams, and
            renewable resources.
          </p>
        </div>
        <nav
          class="saved-worlds"
          aria-label="Saved worlds"
        >
          <h3>Your worlds</h3>
          <p>Choose a world to watch.</p>
          <section
            v-if="deleting"
            aria-label="Delete world confirmation"
            class="delete-world-confirmation"
          >
            <h3>Delete {{ deleting.name }}?</h3>
            <p>This permanently removes its inhabitants, memories, messages, creations, history, and recordings.</p>
            <GameButton
              label="Cancel deletion"
              :disabled="store.busy"
              @click="deleting = null"
            />
            <GameButton
              label="Delete permanently"
              :disabled="store.busy"
              :loading="store.busy"
              @click="confirmDelete"
            />
          </section>
          <template v-else>
            <div
              v-for="world in store.worlds"
              :key="world.id"
              class="saved-world-row"
            >
              <button
                type="button"
                class="saved-world"
                :aria-label="`Open ${world.name}`"
                :disabled="store.busy || store.loading"
                @click="store.openSavedWorld(world.id)"
              >
                <span class="saved-world-icon"><Trees :size="22" /></span>
                <span
                  ><strong>{{ world.name }}</strong
                  ><small
                    >{{ world.configuration.rulesVersion === 1 ? "Early landscape" : "Forests & streams" }} ·
                    {{ formatWorldTime(world.id === store.world?.id ? store.world.tick : world.tick) }}</small
                  ></span
                >
                <ChevronRight :size="18" />
              </button>
              <GameButton
                :label="`Delete ${world.name}`"
                :icon="Trash2"
                icon-only
                :disabled="store.busy || store.loading"
                @click="deleting = world"
              />
            </div>
          </template>
          <p v-if="!store.worlds.length">No saved worlds yet. Create a new beginning.</p>
        </nav>
      </div>
      <p
        v-if="store.error"
        role="alert"
        class="profile-error"
      >
        {{ store.error }}
      </p>
      <footer>
        <template v-if="store.busy">Saving this moment…</template>
        <template v-else-if="store.world?.status === 'running'"
          >This world is still running.
          <GameButton
            label="Pause world"
            :icon="Pause"
            @click="store.openMenu()"
        /></template>
        <template v-else
          >Worlds are saved automatically. Your current world is paused while this menu is open.</template
        >
      </footer>
    </section>
  </GameDialog>
</template>
<script setup lang="ts">
  import { assetUrl, formatWorldTime } from "@/features/worlds/presentation";
  import GameButton from "@/views/Worlds/GameButton.vue";
  import GameDialog from "@/views/Worlds/GameDialog.vue";
  import { useWorldsStore } from "@/views/Worlds/worldsStore";
  import { ChevronRight, Pause, Play, Plus, Trash2, Trees, X } from "@lucide/vue";
  import type { WorldSummary } from "@/types/worlds/WorldInterface";
  import { ref } from "vue";

  const store = useWorldsStore();
  const deleting = ref<WorldSummary | null>(null);

  async function confirmDelete() {
    if (!deleting.value) return;

    const id = deleting.value.id;
    await store.deleteWorld(id);

    if (!store.worlds.some((world) => world.id === id)) deleting.value = null;
  }

  function close() {
    if (store.busy || store.loading) return;

    if (deleting.value) deleting.value = null;
    else if (store.world) store.showMenu = false;
  }
</script>
