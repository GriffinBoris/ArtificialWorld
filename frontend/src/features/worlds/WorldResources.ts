import { type AssetName, WorldAssets, disposeWorldObject } from "@/features/worlds/WorldAssets";
import type { WorldEntity } from "@/types/worlds/WorldInterface";
import * as THREE from "three";

function variation(entity: WorldEntity) {
  return Math.abs(Math.floor(entity.position[0] * 17 + entity.position[1] * 31));
}

function resourceAsset(entity: WorldEntity): AssetName {
  if (entity.resource?.growthSeconds) {
    const growth = entity.mass / entity.resource.capacity;

    if (entity.resource.felledTick !== null && growth < 0.005) return "stump";

    if (growth < 0.15) return "sapling";
  }

  if (entity.material === "wood") return variation(entity) % 3 === 0 ? "pine" : "tree";

  return ({ stone: "rock", food: "berry-bush", fiber: "reeds" } as Record<string, AssetName>)[entity.material];
}

export class WorldResources {
  readonly root = new THREE.Group();
  private signature = "";
  private selection = new THREE.Mesh(
    new THREE.RingGeometry(0.75, 0.83, 40),
    new THREE.MeshBasicMaterial({ color: "#fff1b0", side: THREE.DoubleSide, depthWrite: false })
  );

  constructor(private assets: WorldAssets) {
    this.selection.visible = false;
    this.selection.raycast = () => {};
    this.root.add(this.selection);
  }

  update(entities: WorldEntity[], selectedId: string | null) {
    const resources = entities.filter((entity) => entity.kind === "resource" && entity.fixed);
    const selected = resources.find((entity) => entity.id === selectedId);
    this.selection.visible = Boolean(selected);

    if (selected)
      this.selection.position.set(
        selected.position[0],
        selected.position[1],
        selected.position[2] - selected.dimensions[2] / 2 + 0.04
      );

    const signature = JSON.stringify(
      resources.map((entity) => [entity.id, resourceAsset(entity), entity.position, entity.rotation, entity.dimensions])
    );

    if (signature === this.signature) return;

    this.signature = signature;

    for (const child of [...this.root.children]) if (child !== this.selection) disposeWorldObject(child);

    const groups = new Map<AssetName, WorldEntity[]>();

    for (const entity of resources) {
      const name = resourceAsset(entity);
      const group = groups.get(name) ?? [];
      group.push(entity);
      groups.set(name, group);
    }

    const transform = new THREE.Object3D();
    const base = new THREE.Matrix4();

    for (const [name, group] of groups) {
      const model = this.assets.create(name, 1).root;
      model.updateMatrixWorld(true);
      model.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;

        const material = Array.isArray(object.material)
          ? object.material.map((item) => item.clone())
          : object.material.clone();
        const mesh = new THREE.InstancedMesh(object.geometry, material, group.length);
        mesh.userData.sharedGeometry = true;
        mesh.userData.entityIds = group.map((entity) => entity.id);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        group.forEach((entity, index) => {
          const height = entity.dimensions[2];
          transform.position.set(...entity.position);
          const [w, x, y, z] = entity.rotation;
          transform.quaternion.set(x, y, z, w);
          transform.scale.setScalar(height);
          transform.updateMatrix();
          base.copy(transform.matrix).multiply(new THREE.Matrix4().makeTranslation(0, 0, -0.5));
          mesh.setMatrixAt(index, base.clone().multiply(object.matrixWorld));
          mesh.setColorAt(index, new THREE.Color().setHSL(0.2, 0.05, 0.85 + (variation(entity) % 4) * 0.04));
        });
        mesh.computeBoundingSphere();
        this.root.add(mesh);
      });
      disposeWorldObject(model);
    }
  }
}
