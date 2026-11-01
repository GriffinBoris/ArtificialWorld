import { assetUrl, inhabitantColor } from "@/features/worlds/presentation";
import type { WorldEntity } from "@/types/worlds/WorldInterface";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { type GLTF, GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const assetNames = [
  "villager",
  "tree",
  "pine",
  "rock",
  "berry-bush",
  "reeds",
  "flowers",
  "branch",
  "cloud",
  "seed",
  "sapling",
  "stump",
] as const;
export type AssetName = (typeof assetNames)[number];

export function disposeWorldObject(root: THREE.Object3D) {
  root.traverse((object) => {
    if (object instanceof THREE.InstancedMesh) object.dispose();

    if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
      if (!object.userData.sharedGeometry) object.geometry.dispose();

      for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose();
    }

    if (object.userData.labelElement instanceof HTMLElement) object.userData.labelElement.remove();
  });
  root.removeFromParent();
}

export class WorldAssets {
  private models = new Map<AssetName, GLTF>();

  async load() {
    const loader = new GLTFLoader();
    const results = await Promise.allSettled(assetNames.map((name) => loader.loadAsync(assetUrl(`${name}.glb`))));
    let failed = false;
    results.forEach((result, index) => {
      if (result.status === "fulfilled") this.models.set(assetNames[index], result.value);
      else failed = true;
    });

    if (failed) throw new Error("The Blender world assets could not be loaded.");
  }

  create(name: AssetName, height: number) {
    const source = this.models.get(name)!;
    const root = new THREE.Group();
    const model = source.scene.clone(true);
    model.rotation.x = Math.PI / 2;
    model.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(model);
    const scale = height / (bounds.max.z - bounds.min.z);
    model.scale.multiplyScalar(scale);
    model.position.z = -bounds.min.z * scale;
    model.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.material = Array.isArray(object.material)
          ? object.material.map((material) => material.clone())
          : object.material.clone();
        object.castShadow = true;
        object.receiveShadow = true;
        object.userData.sharedGeometry = true;
      }
    });
    root.add(model);

    return { root, model, clips: source.animations };
  }

  entity(entity: WorldEntity) {
    const root = new THREE.Group();
    const height = entity.dimensions[2];
    let name: AssetName | null = null;

    if (entity.kind === "inhabitant" || entity.kind === "corpse") name = "villager";
    else if (entity.kind === "seed") name = "seed";
    else if (entity.kind === "resource")
      name = ({ wood: "tree", stone: "rock", food: "berry-bush", fiber: "reeds" } as Record<string, AssetName>)[
        entity.material
      ];
    else if (
      entity.material === "wood" &&
      !entity.resource &&
      height > entity.dimensions[0] * 6 &&
      height > entity.dimensions[1] * 6
    )
      name = "branch";

    let mixer: THREE.AnimationMixer | null = null;
    const actions = new Map<string, THREE.AnimationAction>();

    if (name) {
      const instance = this.create(name, height);
      instance.root.position.z = -height / 2;
      root.add(instance.root);

      if (name === "villager") {
        instance.model.traverse((object) => {
          if (
            object instanceof THREE.Mesh &&
            object.material instanceof THREE.MeshStandardMaterial &&
            object.material.name === "shirt"
          )
            object.material.color.set(inhabitantColor(entity.id));
        });
        mixer = new THREE.AnimationMixer(instance.model);

        for (const clip of instance.clips) actions.set(clip.name, mixer.clipAction(clip));

        actions.get("Idle")?.play();
        mixer.update(parseInt(entity.id.slice(-2), 16) / 60);
      }
    } else {
      const [x, y, z] = entity.dimensions;
      let geometry: THREE.BufferGeometry;

      if (entity.shape === "sphere") geometry = new THREE.IcosahedronGeometry(x / 2, 1);
      else if (entity.shape === "cylinder") {
        geometry = new THREE.CylinderGeometry(x / 2, x / 2, z, 10);
        geometry.rotateX(Math.PI / 2);
      } else geometry = new RoundedBoxGeometry(x, y, z, 2, Math.min(x, y, z) * 0.12);

      const colors: Record<string, string> = {
        wood: "#c99b70",
        stone: "#b7c5d6",
        fiber: "#dcca86",
        food: "#ed94a6",
        body: "#f5cdb1",
      };
      const mesh = new THREE.Mesh(
        geometry,
        new THREE.MeshStandardMaterial({ color: colors[entity.material], roughness: 0.9, flatShading: true })
      );
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      root.add(mesh);
    }

    root.userData.entityId = entity.id;

    return { root, mixer, actions };
  }

  dispose() {
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();

    for (const model of this.models.values())
      model.scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          geometries.add(object.geometry);

          for (const material of Array.isArray(object.material) ? object.material : [object.material])
            materials.add(material);
        }
      });

    geometries.forEach((geometry) => geometry.dispose());
    materials.forEach((material) => material.dispose());
    this.models.clear();
  }
}
