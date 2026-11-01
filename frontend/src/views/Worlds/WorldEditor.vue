<template>
  <details class="border-line rounded-md border p-4">
    <summary class="cursor-pointer text-sm font-medium">World editor</summary>
    <p class="text-secondary my-4 text-xs">
      Place or move physical objects and adjust an inhabitant's condition. Every intervention is recorded. Pause the
      world to edit.
    </p>
    <form
      class="flex flex-wrap items-end gap-4"
      @submit.prevent="apply"
    >
      <label class="grid min-w-40 gap-2 text-xs"
        >Edit
        <AppSelect
          v-model="kind"
          :options="editOptions"
          option-label="label"
          option-value="value"
          input-id="edit-kind"
          aria-label="Edit"
          overlay-class="game-select-overlay"
          :disabled="disabled || saving"
        />
      </label>
      <template v-if="kind === 'create'">
        <label class="grid min-w-40 gap-2 text-xs"
          >Object name<AppInputText
            v-model="name"
            :disabled="disabled || saving"
            input-id="part-name"
        /></label>
        <label class="grid min-w-32 gap-2 text-xs"
          >Material<AppSelect
            v-model="material"
            :options="materialOptions"
            option-label="label"
            option-value="value"
            :disabled="disabled || saving"
            input-id="part-material"
            aria-label="Material"
            overlay-class="game-select-overlay"
        /></label>
        <label class="flex items-center gap-2 text-xs"
          ><input
            v-model="fixed"
            type="checkbox"
            :disabled="disabled || saving"
          />Fixed resource deposit</label
        >
      </template>
      <template v-if="kind === 'create' || kind === 'move'">
        <label
          v-for="axis in axes"
          :key="axis"
          class="grid w-24 gap-2 text-xs"
          >{{ axis.toUpperCase() }} (m)<AppInputText
            v-model="position[axis]"
            type="number"
            :input-id="`edit-${axis}`"
            :disabled="disabled || saving"
        /></label>
      </template>
      <template v-if="kind === 'body'">
        <label class="grid min-w-32 gap-2 text-xs"
          >Condition<AppSelect
            v-model="metric"
            :options="metricOptions"
            option-label="label"
            option-value="value"
            :disabled="disabled || saving"
            input-id="body-metric"
            aria-label="Condition"
            overlay-class="game-select-overlay"
        /></label>
        <label class="grid w-24 gap-2 text-xs"
          >Value (0–100)<AppInputText
            v-model="value"
            type="number"
            :disabled="disabled || saving"
            input-id="body-value"
        /></label>
      </template>
      <AppButton
        :label="kind === 'create' ? 'Place block' : 'Apply edit'"
        button-type="submit"
        :disabled="disabled || !kind || (!['create', 'ecology'].includes(kind) && !selectedEntity)"
        :loading="saving"
        test-id="apply-world-edit"
      />
    </form>
    <p
      v-if="kind === 'ecology'"
      class="text-secondary mt-3 text-xs"
    >
      Add plant regrowth, naturally reseeding areas, and inexhaustible quarry sources to this world's existing
      resources. Its terrain, people, and recorded history stay intact.
    </p>
    <p
      v-if="selectedEntity && !['create', 'ecology'].includes(kind ?? '')"
      class="text-secondary mt-3 text-xs"
    >
      Selected: {{ selectedEntity.name }}
    </p>
    <p
      v-if="error"
      role="alert"
      class="text-error mt-3 text-xs"
    >
      {{ error }}
    </p>
  </details>
</template>

<script setup lang="ts">
  import AppButton from "@/components/ui/AppButton.vue";
  import AppInputText from "@/components/ui/AppInputText.vue";
  import AppSelect from "@/components/ui/AppSelect.vue";
  import { worldsApi } from "@/features/worlds/api";
  import type { NewPartRequest, WorldEditRequest } from "@/types/worlds/WorldRequestInterface";
  import type { WorldDetail, WorldEntity } from "@/types/worlds/WorldInterface";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { onBeforeUnmount, ref, watch } from "vue";

  const props = defineProps<{ worldId: string; selectedEntity?: WorldEntity; disabled: boolean }>();
  const emit = defineEmits<{ updated: [world: WorldDetail] }>();
  const kind = ref<WorldEditRequest["kind"] | null>("create");
  const metric = ref<"food" | "water" | "energy" | "health" | "wear" | "injury" | "stress" | null>("food");
  const value = ref("100");
  const name = ref("Placed block");
  const material = ref<NewPartRequest["material"] | null>("wood");
  const fixed = ref(false);
  const position = ref({ x: "0", y: "0", z: "5" });
  const axes = ["x", "y", "z"] as const;
  const saving = ref(false);
  const error = ref("");
  const editOptions = [
    { label: "Place a block", value: "create" },
    { label: "Move selected object", value: "move" },
    { label: "Adjust selected inhabitant", value: "body" },
    { label: "Remove selected object", value: "remove" },
    { label: "Enable renewable resources", value: "ecology" },
  ];
  const materialOptions = ["wood", "stone", "fiber", "food"].map((item) => ({ label: item, value: item }));
  const metricOptions = ["food", "water", "energy", "health", "wear", "injury", "stress"].map((item) => ({
    label: item,
    value: item,
  }));
  let generation = 0;
  watch(
    () => [props.worldId, props.selectedEntity?.id, kind.value],
    () => {
      generation++;
      error.value = "";
      const point = props.selectedEntity?.position ?? [0, 0, 5];
      position.value = {
        x: (point[0] + (kind.value === "create" ? 1.5 : 0)).toFixed(2),
        y: point[1].toFixed(2),
        z: (point[2] + (kind.value === "create" ? 1 : 0)).toFixed(2),
      };
    },
    { immediate: true }
  );

  async function apply() {
    if (!kind.value) return;

    const point: [number, number, number] = [
      Number(position.value.x),
      Number(position.value.y),
      Number(position.value.z),
    ];
    const targetId = props.selectedEntity?.id;
    let edit: WorldEditRequest;

    if (kind.value === "ecology") {
      edit = { kind: "ecology" };
    } else if (kind.value === "create") {
      if (!material.value) return;

      edit = {
        kind: "create",
        part: {
          name: name.value,
          material: material.value,
          shape: "box",
          dimensions: [0.5, 0.5, 0.5],
          position: point,
          fixed: fixed.value,
          kind: fixed.value ? "resource" : "part",
        },
      };
    } else {
      if (!targetId || !metric.value) return;

      edit =
        kind.value === "move"
          ? { kind: "move", targetId, position: point }
          : kind.value === "remove"
            ? { kind: "remove", targetId }
            : { kind: "body", targetId, metric: metric.value, value: Number(value.value) };
    }

    const current = generation;
    saving.value = true;
    error.value = "";

    try {
      const result = await worldsApi.edit(props.worldId, edit);

      if (current === generation) emit("updated", result);
    } catch (failure) {
      if (current === generation) error.value = getFirstApiErrorMessage(failure, "Could not apply this edit.");
    } finally {
      saving.value = false;
    }
  }
  onBeforeUnmount(() => {
    generation++;
  });
</script>
