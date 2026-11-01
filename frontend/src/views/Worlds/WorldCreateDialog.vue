<template>
  <GameDialog
    label="Create a world"
    @close="close"
  >
    <section class="game-modal game-panel">
      <header>
        <span class="modal-flower">✿</span
        ><GameButton
          label="Close new world"
          :icon="X"
          icon-only
          :disabled="store.busy"
          @click="close"
        />
      </header>
      <h2>A new little beginning.</h2>
      <p>Dense forests, rocky outcrops, streams, ponds, and renewable resources.</p>
      <form @submit.prevent="store.createWorld()">
        <label for="world-name">World name</label>
        <AppInputText
          v-model="store.newName"
          input-id="world-name"
          required
          maxlength="120"
          :disabled="store.busy"
          autofocus
        />
        <label for="world-seed">Landscape seed</label>
        <AppInputText
          :model-value="String(store.newSeed)"
          input-id="world-seed"
          type="number"
          required
          min="0"
          max="2147483647"
          step="1"
          :disabled="store.busy"
          @update:model-value="store.newSeed = Number($event)"
        />
        <label for="world-population">Starting inhabitants</label>
        <AppInputText
          :model-value="String(store.newPopulation)"
          input-id="world-population"
          type="number"
          required
          min="1"
          max="10"
          step="1"
          :disabled="store.busy"
          @update:model-value="store.newPopulation = Number($event)"
        />
        <small>A 1,024 m world · choose 1–10 founders · AI calls start off</small>
        <p
          v-if="store.error"
          role="alert"
          class="profile-error"
        >
          {{ store.error }}
        </p>
        <GameButton
          label="Begin a world"
          :icon="Sprout"
          primary
          button-type="submit"
          :loading="store.busy"
          :disabled="!store.newName.trim()"
          test-id="generate-world"
        />
      </form>
    </section>
  </GameDialog>
</template>
<script setup lang="ts">
  import AppInputText from "@/components/ui/AppInputText.vue";
  import GameButton from "@/views/Worlds/GameButton.vue";
  import GameDialog from "@/views/Worlds/GameDialog.vue";
  import { useWorldsStore } from "@/views/Worlds/worldsStore";
  import { Sprout, X } from "@lucide/vue";
  const store = useWorldsStore();
  function close() {
    if (!store.busy) store.showCreate = false;
  }
</script>
