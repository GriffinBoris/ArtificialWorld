<template>
  <div class="minimap game-panel">
    <div class="minimap-top"><Compass :size="13" /><span>Around here</span><span>N ↑</span></div>
    <canvas
      ref="canvas"
      width="180"
      height="150"
      aria-label="Nearby world map. Click to move the camera."
      @click="focus"
    />
    <p><span class="map-dot" />{{ store.livingCount }} little lives</p>
  </div>
</template>
<script setup lang="ts">
  import { heightAt } from "@/features/worlds/WorldScenery";
  import { inhabitantColor } from "@/features/worlds/presentation";
  import type { Vector3Tuple } from "@/types/worlds/WorldInterface";
  import { useWorldsStore } from "@/views/Worlds/worldsStore";
  import { Compass } from "@lucide/vue";
  import { computed, onMounted, ref, watch } from "vue";
  const emit = defineEmits<{ focus: [position: Vector3Tuple] }>();
  const store = useWorldsStore();
  const canvas = ref<HTMLCanvasElement>();
  const center = computed(() => store.selectedEntity?.position ?? [0, 0, 0]);
  const radius = 95;
  function draw() {
    const context = canvas.value?.getContext("2d");

    if (!context || !store.terrain || !store.displayState) return;

    for (let y = 0; y < 150; y += 3)
      for (let x = 0; x < 180; x += 3) {
        const height = heightAt(
          store.terrain,
          center.value[0] + (x / 180 - 0.5) * radius * 2,
          center.value[1] - (y / 150 - 0.5) * radius * 2
        );
        context.fillStyle =
          height < store.terrain.waterLevel ? "#9ad2d2" : height < store.terrain.waterLevel + 1 ? "#e6d6ac" : "#c0d49e";
        context.fillRect(x, y, 3, 3);
      }

    for (const entity of store.displayState.entities) {
      const x = 90 + ((entity.position[0] - center.value[0]) / (radius * 2)) * 180,
        y = 75 - ((entity.position[1] - center.value[1]) / (radius * 2)) * 150;

      if (entity.kind !== "resource" && entity.kind !== "inhabitant") continue;

      context.fillStyle =
        entity.kind === "inhabitant" ? inhabitantColor(entity.id) : entity.material === "wood" ? "#8fb38a" : "#a1b6a2";
      context.beginPath();
      context.arc(x, y, entity.kind === "inhabitant" ? 3 : 1.8, 0, Math.PI * 2);
      context.fill();

      if (entity.id === store.selectedId) {
        context.strokeStyle = "#fffdf3";
        context.lineWidth = 2;
        context.stroke();
      }
    }
  }
  function focus(event: MouseEvent) {
    if (!canvas.value || !store.terrain) return;

    const box = canvas.value.getBoundingClientRect();
    const x = center.value[0] + ((event.clientX - box.left) / box.width - 0.5) * radius * 2;
    const y = center.value[1] - ((event.clientY - box.top) / box.height - 0.5) * radius * 2;
    emit("focus", [x, y, heightAt(store.terrain, x, y)]);
  }
  onMounted(draw);
  watch(() => [store.displayState, store.selectedId, store.terrain], draw);
</script>
