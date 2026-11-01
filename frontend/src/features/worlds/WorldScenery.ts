import { WorldAssets, disposeWorldObject } from "@/features/worlds/WorldAssets";
import { createWater } from "@/features/worlds/WorldWater";
import type { Terrain } from "@/types/worlds/WorldInterface";
import * as THREE from "three";

export function heightAt(terrain: Terrain, x: number, y: number) {
  const cells = terrain.heights.length - 1;
  const u = THREE.MathUtils.clamp((x / terrain.size + 0.5) * cells, 0, cells - 0.0001);
  const v = THREE.MathUtils.clamp((y / terrain.size + 0.5) * cells, 0, cells - 0.0001);
  const column = Math.floor(u),
    row = Math.floor(v),
    fx = u - column,
    fy = v - row;
  const a = terrain.heights[row][column],
    b = terrain.heights[row][column + 1],
    c = terrain.heights[row + 1][column],
    d = terrain.heights[row + 1][column + 1];

  return fx + fy <= 1 ? a + (b - a) * fx + (c - a) * fy : d + (c - d) * (1 - fx) + (b - d) * (1 - fy);
}

export function seededRandom(seed: number) {
  let value = seed || 1;

  return () => {
    value ^= value << 13;
    value ^= value >>> 17;
    value ^= value << 5;

    return (value >>> 0) / 4294967296;
  };
}

export function createScenery(terrain: Terrain, assets: WorldAssets, seed: number) {
  const root = new THREE.Group();
  const resolution = terrain.heights.length - 1;
  const geometry = new THREE.PlaneGeometry(terrain.size, terrain.size, resolution, resolution);
  const position = geometry.attributes.position;
  const colors: number[] = [];

  for (let index = 0; index < position.count; index++) {
    const height = terrain.heights[resolution - Math.floor(index / (resolution + 1))][index % (resolution + 1)];
    position.setZ(index, height);
    const x = position.getX(index),
      y = position.getY(index);
    const color = new THREE.Color(height < terrain.waterLevel + 1.4 ? "#e9d7a4" : "#95bd70");

    if (height > 22) color.lerp(new THREE.Color("#9baab6"), THREE.MathUtils.smoothstep(height, 22, 37));

    if (height > 44) color.lerp(new THREE.Color("#eef1e8"), THREE.MathUtils.smoothstep(height, 44, 55));

    color.multiplyScalar(0.94 + Math.sin(x / 17 + seed) * Math.cos(y / 21) * 0.07 + Math.sin(index * 12.9898) * 0.035);
    colors.push(color.r, color.g, color.b);
  }

  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.computeVertexNormals();
  const ground = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true })
  );
  ground.receiveShadow = true;
  root.add(ground);
  const water = createWater(terrain);
  root.add(water.mesh);
  const random = seededRandom(seed + 81);
  const points: THREE.Matrix4[] = [];
  const transform = new THREE.Object3D();

  for (let index = 0; index < 650; index++) {
    const angle = random() * Math.PI * 2,
      radius = 6 + random() * 150;
    const x = Math.cos(angle) * radius,
      y = Math.sin(angle) * radius;
    const height = heightAt(terrain, x, y);

    if (height < terrain.waterLevel + 0.6) continue;

    transform.position.set(x, y, height + 0.015);
    transform.rotation.set(0, 0, random() * Math.PI * 2);
    transform.scale.setScalar(0.6 + random() * 0.9);
    transform.updateMatrix();
    points.push(transform.matrix.clone());
  }

  const flowers = assets.create("flowers", 0.36).root;
  flowers.updateMatrixWorld(true);
  flowers.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;

    const instanced = new THREE.InstancedMesh(object.geometry, object.material.clone(), points.length);
    instanced.userData.sharedGeometry = true;
    points.forEach((matrix, index) => instanced.setMatrixAt(index, matrix.clone().multiply(object.matrixWorld)));
    instanced.receiveShadow = true;
    instanced.computeBoundingSphere();
    root.add(instanced);
  });
  disposeWorldObject(flowers);
  const clouds: { root: THREE.Group; x: number; phase: number; speed: number }[] = [];

  for (let index = 0; index < 22; index++) {
    const cloud = assets.create("cloud", 3.5 + random() * 3.5).root;
    cloud.position.set(-160 + random() * 320, 32 + random() * 230, 23 + random() * 20);
    cloud.position.z = Math.max(cloud.position.z, heightAt(terrain, cloud.position.x, cloud.position.y) + 15);
    cloud.rotation.z = random() * Math.PI;
    cloud.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.castShadow = false;
        object.receiveShadow = false;
      }
    });
    root.add(cloud);
    clouds.push({ root: cloud, x: cloud.position.x, phase: random() * Math.PI * 2, speed: 0.025 + random() * 0.02 });
  }

  const ripples: THREE.Mesh<THREE.RingGeometry, THREE.MeshBasicMaterial>[] = [];

  for (let index = 0; index < 22; index++) {
    const x = 70 + random() * 90,
      y = 35 + random() * 90;

    if (heightAt(terrain, x, y) > terrain.waterLevel - 0.2) continue;

    const ripple = new THREE.Mesh(
      new THREE.RingGeometry(1, 1.04, 40),
      new THREE.MeshBasicMaterial({ color: "#f3fff4", transparent: true, opacity: 0.16, depthWrite: false })
    );
    ripple.position.set(x, y, terrain.waterLevel + 0.035);
    ripple.scale.setScalar(1 + random() * 3);
    root.add(ripple);
    ripples.push(ripple);
  }

  return {
    root,
    animate(time: number) {
      water.animate(time);
      clouds.forEach((cloud) => {
        cloud.root.position.x = cloud.x + Math.sin(time * cloud.speed + cloud.phase) * 12;
      });
      ripples.forEach((ripple, index) => {
        ripple.material.opacity = 0.13 + Math.sin(time + index) * 0.06;
      });
    },
    dispose: water.dispose,
  };
}
