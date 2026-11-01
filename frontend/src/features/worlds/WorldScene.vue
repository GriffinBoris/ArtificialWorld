<template>
  <div
    ref="container"
    class="world-scene"
    data-testid="world-scene"
    :data-tick="state.tick"
  >
    <svg
      ref="speechTails"
      class="speech-tails"
      aria-hidden="true"
    />
    <div
      v-if="!ready && !renderError"
      class="scene-loading"
    >
      <span>✿</span>
      <p>Growing a little world…</p>
    </div>
    <div
      v-if="renderError"
      role="alert"
      class="scene-loading"
    >
      <span>☁</span>
      <p>{{ renderError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { InhabitantAnimation } from "@/features/worlds/InhabitantAnimation";
  import { inhabitantColor } from "@/features/worlds/presentation";
  import { placeSpeechBubble, type SpeechBounds } from "@/features/worlds/speechLayout";
  import { disposeWorldObject, WorldAssets } from "@/features/worlds/WorldAssets";
  import { createScenery, heightAt } from "@/features/worlds/WorldScenery";
  import { WorldResources } from "@/features/worlds/WorldResources";
  import type { Terrain, Vector3Tuple, WorldMessage, WorldState } from "@/types/worlds/WorldInterface";
  import * as THREE from "three";
  import { OrbitControls } from "three/addons/controls/OrbitControls.js";
  import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
  import { onBeforeUnmount, onMounted, ref, watch } from "vue";

  const props = defineProps<{
    state: WorldState;
    terrain: Terrain;
    selectedId: string | null;
    messages: WorldMessage[];
    replay: boolean;
    running: boolean;
    motionPlaying: boolean;
    followId: string | null;
    interactive: boolean;
  }>();
  const emit = defineEmits<{ select: [id: string]; conversation: [id: string]; thinking: [id: string] }>();
  const container = ref<HTMLDivElement>();
  const speechTails = ref<SVGSVGElement>();
  const ready = ref(false);
  const renderError = ref("");
  const assets = new WorldAssets();
  type Visual = ReturnType<WorldAssets["entity"]> & {
    target: THREE.Vector3;
    rotation: THREE.Quaternion;
    signature: string;
    animation?: InhabitantAnimation;
    label?: CSS2DObject;
    labelSignature?: string;
    tail?: SVGPathElement;
    ring?: THREE.Mesh;
    heading: number;
  };
  const visuals = new Map<string, Visual>();
  const raycaster = new THREE.Raycaster();
  const projected = new THREE.Vector3();
  const zAxis = new THREE.Vector3(0, 0, 1);
  let renderer: THREE.WebGLRenderer | null = null;
  let labels: CSS2DRenderer | null = null;
  let camera: THREE.PerspectiveCamera | null = null;
  let controls: OrbitControls | null = null;
  let scene: THREE.Scene | null = null;
  let scenery: ReturnType<typeof createScenery> | null = null;
  let resources: WorldResources | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let frameId = 0;
  let disposed = false;
  let previousTime = 0;
  let lastTick = props.state.tick;
  let secondsSinceProgress = Infinity;
  let labelInsets = { left: 0, right: 0, width: 0, height: 0 };
  let pointerStart = { x: 0, y: 0 };
  let cameraGoal: THREE.Vector3 | null = null;

  function focusPoint(point: Vector3Tuple) {
    cameraGoal = new THREE.Vector3(...point);
  }
  function focusSelected() {
    const entity = props.state.entities.find((entity) => entity.id === props.selectedId);

    if (entity) focusPoint(entity.position);
    else resetView();
  }
  function resetView() {
    if (!camera || !controls) return;

    const first = props.state.entities.find((entity) => entity.id === props.state.inhabitants[0]?.id);
    const x = first?.position[0] ?? 0,
      y = first?.position[1] ?? 0;
    controls.target.set(x + 2, y + 3, heightAt(props.terrain, x, y) + 0.5);
    camera.position.copy(controls.target).add(new THREE.Vector3(22, -28, 25));
    cameraGoal = null;
    controls.update();
  }
  function zoom(amount: number) {
    if (camera && controls)
      camera.position.copy(controls.target).add(camera.position.clone().sub(controls.target).multiplyScalar(amount));
  }
  function landscapeView() {
    if (!camera || !controls) return;

    controls.target.set(0, 70, 8);
    camera.position.copy(controls.target).add(new THREE.Vector3(95, -175, 125));
    cameraGoal = null;
    controls.update();
  }
  defineExpose({ resetView, focusPoint, focusSelected, zoom, landscapeView });

  function createLabel(id: string, height: number) {
    const element = document.createElement("div");
    element.className = "inhabitant-label";
    element.style.setProperty("--inhabitant-color", inhabitantColor(id));
    const label = new CSS2DObject(element);
    label.center.set(0.5, 1);
    label.position.z = height / 2 + 0.6;
    label.userData.labelElement = element;

    return label;
  }
  function updateLabels() {
    const recentSpeakers = [
      ...new Set(
        [...props.messages]
          .reverse()
          .filter((message) => message.tick <= props.state.tick && props.state.tick - message.tick <= 60 * 12)
          .map((message) => message.speakerId)
      ),
    ].slice(0, 3);

    for (const agent of props.state.inhabitants) {
      const visual = visuals.get(agent.id);

      if (!visual?.label) continue;

      const last = [...props.messages]
        .reverse()
        .find((message) => message.speakerId === agent.id && message.tick <= props.state.tick);
      const speaking =
        last &&
        props.state.tick - last.tick <= 60 * 12 &&
        (props.selectedId ? props.selectedId === agent.id : recentSpeakers.includes(agent.id));
      const thinking = props.running && agent.driver === "pydantic" && !agent.activity && agent.alive;
      const signature = JSON.stringify([
        agent.name,
        props.selectedId === agent.id,
        speaking ? last.id : null,
        thinking && !speaking,
      ]);

      if (visual.labelSignature === signature) continue;

      visual.labelSignature = signature;
      const element = visual.label.element;
      element.replaceChildren();
      visual.tail?.remove();
      visual.tail = undefined;

      if (speaking || thinking) {
        const bubble = document.createElement("button");
        bubble.type = "button";
        bubble.className = `speech-bubble${thinking && !speaking ? " thinking-bubble" : ""}`;
        bubble.textContent = speaking ? last.text : "● ● ●";
        bubble.setAttribute("aria-label", `${speaking ? "Conversation with" : "Decision activity for"} ${agent.name}`);
        bubble.dataset.testid = `speech-${agent.id}`;
        bubble.addEventListener("pointerdown", (event) => event.stopPropagation());
        bubble.addEventListener("wheel", (event) => event.stopPropagation());
        bubble.addEventListener("keydown", (event) => {
          switch (event.key) {
            case "ArrowDown":
              bubble.scrollTop += 32;
              break;
            case "ArrowUp":
              bubble.scrollTop -= 32;
              break;
            case "PageDown":
              bubble.scrollTop += bubble.clientHeight;
              break;
            case "PageUp":
              bubble.scrollTop -= bubble.clientHeight;
              break;
            case "Home":
              bubble.scrollTop = 0;
              break;
            case "End":
              bubble.scrollTop = bubble.scrollHeight;
              break;
            default:
              return;
          }

          event.preventDefault();
          event.stopPropagation();
        });
        bubble.addEventListener("click", () =>
          speaking ? emit("conversation", agent.id) : emit("thinking", agent.id)
        );
        element.append(bubble);
        visual.tail = document.createElementNS("http://www.w3.org/2000/svg", "path");
        speechTails.value?.append(visual.tail);
      }

      const name = document.createElement("button");
      name.type = "button";
      name.className = `inhabitant-name${props.selectedId === agent.id ? " selected" : ""}`;
      name.textContent = agent.name;
      name.setAttribute("aria-label", `Meet ${agent.name}`);
      name.addEventListener("pointerdown", (event) => event.stopPropagation());
      name.addEventListener("click", () => emit("select", agent.id));
      element.append(name);
    }
  }
  function positionBubbles() {
    if (!container.value || !camera) return;

    const origin = container.value.getBoundingClientRect();
    const viewport = {
      x: labelInsets.left,
      y: 86,
      width: labelInsets.width - labelInsets.left - labelInsets.right,
      height: labelInsets.height - 200,
    };
    const placed: SpeechBounds[] = [];
    for (const visual of visuals.values()) {
      if (!visual.label?.visible) continue;

      const bounds = visual.label.element.getBoundingClientRect();
      projected.copy(visual.root.position);
      projected.z -= visual.label.position.z - 0.6;
      projected.project(camera);
      const feet = ((1 - projected.y) * labelInsets.height) / 2;
      placed.push({
        x: bounds.left - origin.left - 8,
        y: bounds.top - origin.top,
        width: bounds.width + 16,
        height: Math.max(40, feet - (bounds.top - origin.top) + 8),
      });
    }
    const ordered = [...visuals.entries()].sort(
      ([a], [b]) => Number(b === props.selectedId) - Number(a === props.selectedId)
    );
    const bubbleCount = ordered.filter(
      ([, visual]) => visual.label?.visible && visual.label.element.querySelector(".speech-bubble")
    ).length;

    const spaceAboveCrowd = Math.min(
      ...ordered
        .filter(([, visual]) => visual.label?.visible && visual.label.element.querySelector(".speech-bubble"))
        .map(([, visual]) => visual.label!.element.getBoundingClientRect().top - origin.top - 12 - viewport.y)
    );
    const columns = Math.max(1, Math.floor(viewport.width / (Math.min(240, labelInsets.width / 2) + 10)));
    const rows = Math.max(1, Math.ceil(Math.min(bubbleCount, 3) / columns));

    for (const [, visual] of ordered) {
      if (visual.tail) visual.tail.style.display = "none";
      if (!visual.label?.visible) continue;

      const bubble = visual.label.element.querySelector<HTMLElement>(".speech-bubble");

      if (!bubble) continue;

      const bounds = visual.label.element.getBoundingClientRect();
      const center = bounds.left - origin.left + bounds.width / 2;
      const top = bounds.top - origin.top;
      bubble.style.maxHeight = `${Math.max(44, Math.min(160, labelInsets.height / 4, spaceAboveCrowd / rows - 12))}px`;
      const rectangle = placeSpeechBubble(
        {
          x: center - bubble.offsetWidth / 2,
          y: top - bubble.offsetHeight - 12,
          width: bubble.offsetWidth,
          height: bubble.offsetHeight,
        },
        { ...viewport, height: Math.min(viewport.height, top - 12 - viewport.y) },
        placed
      );
      bubble.style.visibility = rectangle ? "visible" : "hidden";

      if (!rectangle) continue;

      placed.push(rectangle);
      bubble.style.left = `${rectangle.x - (bounds.left - origin.left)}px`;
      bubble.style.top = `${rectangle.y - top}px`;

      if (visual.tail) {
        visual.label.getWorldPosition(projected);
        projected.z -= 0.6;
        projected.project(camera);
        const endX = ((projected.x + 1) * labelInsets.width) / 2;
        const endY = ((1 - projected.y) * labelInsets.height) / 2;
        const startX = THREE.MathUtils.clamp(endX, rectangle.x + 8, rectangle.x + rectangle.width - 8);
        const startY = THREE.MathUtils.clamp(endY, rectangle.y + 4, rectangle.y + rectangle.height);
        const angle = Math.atan2(endY - startY, endX - startX);
        const dx = Math.sin(angle) * 4;
        const dy = Math.cos(angle) * 4;
        visual.tail.setAttribute(
          "d",
          `M ${startX - dx} ${startY + dy} L ${endX} ${endY} L ${startX + dx} ${startY - dy} Z`
        );
        visual.tail.style.display = "";
      }
    }
  }
  function updateEntities(teleport = false) {
    if (!scene || !ready.value) return;

    resources?.update(props.state.entities, props.selectedId);
    const entities = props.state.entities.filter((entity) => entity.kind !== "resource" || !entity.fixed);
    const present = new Set(entities.map((entity) => entity.id));

    for (const [id, visual] of visuals)
      if (!present.has(id)) {
        visual.mixer?.stopAllAction();
        disposeWorldObject(visual.root);
        visual.tail?.remove();
        visuals.delete(id);
      }

    for (const entity of entities) {
      const signature = JSON.stringify([entity.shape, entity.dimensions, entity.kind, entity.material]);
      let visual = visuals.get(entity.id);

      if (visual && visual.signature !== signature) {
        visual.mixer?.stopAllAction();
        disposeWorldObject(visual.root);
        visual.tail?.remove();
        visuals.delete(entity.id);
        visual = undefined;
      }

      if (!visual) {
        visual = {
          ...assets.entity(entity),
          target: new THREE.Vector3(...entity.position),
          rotation: new THREE.Quaternion(),
          signature,
          heading: 0,
        };

        if (visual.mixer)
          visual.animation = new InhabitantAnimation(
            visual.mixer,
            visual.actions,
            parseInt(entity.id.slice(-2), 16) / 60
          );

        visual.root.position.copy(visual.target);

        if (entity.kind === "inhabitant" || entity.kind === "corpse") {
          visual.label = createLabel(entity.id, entity.dimensions[2]);
          visual.root.add(visual.label);
          visual.ring = new THREE.Mesh(
            new THREE.RingGeometry(0.58, 0.67, 40),
            new THREE.MeshBasicMaterial({
              color: "#fff1b0",
              transparent: true,
              opacity: 0.9,
              depthWrite: false,
              side: THREE.DoubleSide,
            })
          );
          visual.ring.position.z = -entity.dimensions[2] / 2 + 0.04;
          visual.root.add(visual.ring);
        }

        scene.add(visual.root);
        visuals.set(entity.id, visual);
      }

      visual.target.set(...entity.position);

      if (entity.kind === "inhabitant") {
        if (Math.hypot(entity.velocity[0], entity.velocity[1]) > 0.08)
          visual.heading = Math.atan2(entity.velocity[0], -entity.velocity[1]);

        visual.rotation.setFromAxisAngle(zAxis, visual.heading);
      } else {
        const [w, x, y, z] = entity.rotation;
        visual.rotation.set(x, y, z, w);
      }

      if (teleport || props.replay) {
        visual.root.position.copy(visual.target);
        visual.root.quaternion.copy(visual.rotation);
      }

      if (visual.ring) visual.ring.visible = props.selectedId === entity.id;
    }

    updateLabels();
  }
  function select(event: PointerEvent) {
    if (
      !props.interactive ||
      !renderer ||
      !camera ||
      Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 5
    )
      return;

    const bounds = renderer.domElement.getBoundingClientRect();
    raycaster.setFromCamera(
      new THREE.Vector2(
        ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
        (-(event.clientY - bounds.top) / bounds.height) * 2 + 1
      ),
      camera
    );
    const hit = raycaster.intersectObjects(
      [...visuals.values()].map((visual) => visual.root).concat(resources ? [resources.root] : []),
      true
    )[0];

    if (hit?.instanceId !== undefined && hit.object.userData.entityIds) {
      emit("select", hit.object.userData.entityIds[hit.instanceId]);

      return;
    }

    let object: THREE.Object3D | undefined = hit?.object;

    while (object && !object.userData.entityId) object = object.parent ?? undefined;

    if (object) emit("select", object.userData.entityId);
  }
  function pointerDown(event: PointerEvent) {
    pointerStart = { x: event.clientX, y: event.clientY };
    cameraGoal = null;
  }
  function keyDown(event: KeyboardEvent) {
    if (
      !props.interactive ||
      event.defaultPrevented ||
      !camera ||
      !controls ||
      (event.target instanceof HTMLElement &&
        event.target.closest(
          "input, textarea, select, button, dialog, [role='combobox'], [role='listbox'], [role='option'], [contenteditable]"
        ))
    )
      return;

    let x = 0;
    let y = 0;

    switch (event.key.toLowerCase()) {
      case "w":
      case "arrowup":
        y = 1;
        break;
      case "s":
      case "arrowdown":
        y = -1;
        break;
      case "a":
      case "arrowleft":
        x = -1;
        break;
      case "d":
      case "arrowright":
        x = 1;
        break;
      default:
        return;
    }

    event.preventDefault();
    const forward = controls.target.clone().sub(camera.position).setZ(0).normalize();
    const right = new THREE.Vector3().crossVectors(forward, zAxis);
    const amount = camera.position.distanceTo(controls.target) * 0.04;
    const offset = right.multiplyScalar(x * amount).add(forward.multiplyScalar(y * amount));
    camera.position.add(offset);
    controls.target.add(offset);
    cameraGoal = null;
  }
  onMounted(async () => {
    if (!container.value) return;

    try {
      await assets.load();

      if (disposed) {
        assets.dispose();

        return;
      }

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.05;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      container.value.prepend(renderer.domElement);
      labels = new CSS2DRenderer();
      labels.domElement.className = "world-labels";
      container.value.append(labels.domElement);
      scene = new THREE.Scene();
      scene.background = new THREE.Color("#d3edf0");
      scene.fog = new THREE.FogExp2("#d3edf0", 0.0018);
      camera = new THREE.PerspectiveCamera(42, 1, 0.1, 2500);
      camera.up.set(0, 0, 1);
      controls = new OrbitControls(camera, renderer.domElement);
      controls.enabled = props.interactive;
      controls.enableDamping = true;
      controls.dampingFactor = 0.07;
      controls.maxPolarAngle = Math.PI / 2 - 0.12;
      controls.minDistance = 5;
      controls.maxDistance = 1000;
      scene.add(new THREE.HemisphereLight("#fff8df", "#96af8c", 1.9));
      const sun = new THREE.DirectionalLight("#fff4d9", 2.7);
      sun.position.set(25, -35, 65);
      sun.castShadow = true;
      sun.shadow.mapSize.set(1024, 1024);
      Object.assign(sun.shadow.camera, { left: -50, right: 50, top: 50, bottom: -50, near: 1, far: 150 });
      sun.shadow.normalBias = 0.04;
      scene.add(sun);
      scenery = createScenery(props.terrain, assets, props.state.config.seed);
      scene.add(scenery.root);
      resources = new WorldResources(assets);
      scene.add(resources.root);
      ready.value = true;
      updateEntities(true);
      resetView();
      resizeObserver = new ResizeObserver(([entry]) => {
        if (!renderer || !camera || !labels) return;

        const { width, height } = entry.contentRect;
        const style = getComputedStyle(container.value!);
        labelInsets = {
          left: parseFloat(style.getPropertyValue("--speech-safe-left")),
          right: parseFloat(style.getPropertyValue("--speech-safe-right")),
          width,
          height,
        };
        renderer.setSize(width, height);
        labels.setSize(width, height);
        camera.aspect = width / Math.max(height, 1);
        camera.updateProjectionMatrix();
      });
      resizeObserver.observe(container.value);
      renderer.domElement.addEventListener("pointerdown", pointerDown);
      renderer.domElement.addEventListener("pointerup", select);
      window.addEventListener("keydown", keyDown);

      function animate(time: number) {
        frameId = requestAnimationFrame(animate);
        const delta = Math.min(0.05, previousTime ? (time - previousTime) / 1000 : 0);
        previousTime = time;

        if (props.state.tick !== lastTick) {
          lastTick = props.state.tick;
          secondsSinceProgress = 0;
        } else secondsSinceProgress += delta;

        for (const [id, visual] of visuals) {
          const moving =
            Math.hypot(visual.root.position.x - visual.target.x, visual.root.position.y - visual.target.y) > 0.03;
          visual.root.position.lerp(visual.target, 1 - Math.exp(-delta * 7));
          visual.root.quaternion.slerp(visual.rotation, 1 - Math.exp(-delta * 8));
          const entity = props.state.entities.find((entity) => entity.id === id)!;
          const agent = props.state.inhabitants.find((agent) => agent.id === id);

          if (visual.animation && agent)
            visual.animation.update(delta, {
              moving,
              speed: Math.hypot(entity.velocity[0], entity.velocity[1]),
              talking:
                agent.activity?.kind === "speak" &&
                (props.replay || ((props.running || props.motionPlaying) && secondsSinceProgress < 1.5)),
              alive: agent.alive,
              replay: props.replay,
              seconds: props.state.tick / props.state.config.physicsHz,
            });

          if (visual.label && camera) {
            projected.copy(visual.root.position).project(camera);
            visual.label.visible =
              projected.z < 1 &&
              Math.abs(projected.x) < 1 &&
              Math.abs(projected.y) < 1 &&
              camera.position.distanceTo(visual.root.position) < 100;
          }

          if (visual.ring?.visible) visual.ring.scale.setScalar(1 + Math.sin(time / 450) * 0.025);
        }

        if (controls && camera) {
          const follow = props.followId ? visuals.get(props.followId)?.root.position : null;
          const goal = follow ?? cameraGoal;

          if (goal) {
            const offset = goal
              .clone()
              .sub(controls.target)
              .multiplyScalar(1 - Math.exp(-delta * 5));
            controls.target.add(offset);
            camera.position.add(offset);

            if (!follow && offset.length() < 0.001) cameraGoal = null;
          }

          controls.update();
        }

        scenery?.animate(props.replay ? props.state.tick / 60 : time / 1000);

        if (renderer && scene && camera) {
          renderer.render(scene, camera);
          labels?.render(scene, camera);
          positionBubbles();
        }
      }

      frameId = requestAnimationFrame(animate);
    } catch {
      renderError.value = "The world could not be rendered. Check WebGL and reload to load its Blender assets.";
      assets.dispose();
    }
  });
  watch(
    () => props.state,
    () => updateEntities()
  );
  watch(() => props.messages, updateLabels);
  watch(() => props.running, updateLabels);
  watch(
    () => props.interactive,
    (enabled) => {
      if (controls) controls.enabled = enabled;
    }
  );
  watch(
    () => props.selectedId,
    () => updateEntities()
  );
  onBeforeUnmount(() => {
    disposed = true;
    cancelAnimationFrame(frameId);
    window.removeEventListener("keydown", keyDown);
    resizeObserver?.disconnect();
    controls?.dispose();
    scenery?.dispose();

    for (const visual of visuals.values()) visual.mixer?.stopAllAction();

    if (scene) disposeWorldObject(scene);

    labels?.domElement.remove();
    renderer?.dispose();
    renderer?.domElement.remove();
    assets.dispose();
    visuals.clear();
  });
</script>

<style scoped>
  .world-scene {
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
    background: #c9e8dc;
  }
  .world-scene :deep(canvas) {
    display: block;
    width: 100%;
    height: 100%;
    outline: none;
  }
  .world-scene :deep(.world-labels) {
    z-index: 2;
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }
  .world-scene :deep(.inhabitant-label) {
    display: flex;
    align-items: center;
    flex-direction: column;
    gap: 7px;
    pointer-events: none;
    padding-bottom: 10px;
  }
  .world-scene :deep(.inhabitant-name) {
    pointer-events: auto;
    border: 0;
    padding: 4px 10px;
    border-radius: 20px;
    color: #39564b;
    font-size: 11px;
    font-weight: 800;
    background: #ffffefdb;
    box-shadow: 0 2px 8px #435b4520;
    white-space: nowrap;
    transition: transform 0.2s;
  }
  .world-scene :deep(.inhabitant-name:hover),
  .world-scene :deep(.inhabitant-name.selected) {
    background: var(--inhabitant-color);
    color: #233d2c;
    transform: translateY(-2px);
  }
  .world-scene :deep(.speech-bubble) {
    position: absolute;
    pointer-events: auto;
    width: max-content;
    max-width: min(240px, 50vw);
    max-height: min(160px, 25dvh);
    color: #4c6055;
    background: #fffdf5;
    border: 2px solid #fff;
    border-radius: 17px 17px 17px 4px;
    padding: 10px 13px;
    font-size: 13px;
    line-height: 1.5;
    font-weight: 600;
    box-shadow:
      0 4px 0 #647a4320,
      0 8px 22px #52643d18;
    display: block;
    text-align: left;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    scrollbar-color: #a7b99c #f5f5e9;
    overscroll-behavior: contain;
    touch-action: pan-y;
  }
  .world-scene :deep(.speech-bubble:hover) {
    background: #fff;
  }
  .speech-tails {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
    fill: #fffdf5;
    stroke: #d9e0d0;
    stroke-width: 1;
  }
  .world-scene :deep(.thinking-bubble) {
    color: #3f6b59;
    letter-spacing: 4px;
    animation: thinking 1.5s ease-in-out infinite;
  }
  .scene-loading {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 12px;
    color: #527765;
    background: #dcecc9;
    font-size: 14px;
    z-index: 1;
  }
  .scene-loading span {
    font-size: 48px;
    color: #edb384;
    animation: thinking 2s ease-in-out infinite;
  }
  @keyframes thinking {
    50% {
      opacity: 0.6;
      transform: translateY(-3px);
    }
  }
</style>
