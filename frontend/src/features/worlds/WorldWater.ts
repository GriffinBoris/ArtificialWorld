import type { Terrain } from "@/types/worlds/WorldInterface";
import * as THREE from "three";

export function createWater(terrain: Terrain) {
  const resolution = terrain.heights.length;
  const heights = new Uint8Array(resolution * resolution);
  terrain.heights.forEach((row, y) =>
    row.forEach((height, x) => {
      heights[y * resolution + x] = Math.round(
        THREE.MathUtils.clamp((height - terrain.waterLevel + 16) / 32, 0, 1) * 255
      );
    })
  );
  const shore = new THREE.DataTexture(heights, resolution, resolution, THREE.RedFormat);
  shore.minFilter = shore.magFilter = THREE.LinearFilter;
  shore.needsUpdate = true;
  const time = { value: 0 };
  const material = new THREE.MeshStandardMaterial({ color: "#53bdcf", roughness: 0.38, metalness: 0.02 });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.waterTime = time;
    shader.uniforms.shoreHeights = { value: shore };
    shader.uniforms.worldSize = { value: terrain.size };
    shader.vertexShader = `varying vec2 waterPosition;\n${shader.vertexShader}`.replace(
      "#include <begin_vertex>",
      "#include <begin_vertex>\nwaterPosition = (modelMatrix * vec4(position, 1.0)).xy;"
    );
    shader.fragmentShader =
      `uniform float waterTime; uniform float worldSize; uniform sampler2D shoreHeights; varying vec2 waterPosition;\n${shader.fragmentShader}`.replace(
        "#include <color_fragment>",
        `#include <color_fragment>
      float ground = texture2D(shoreHeights, waterPosition / worldSize + 0.5).r * 32.0 - 16.0;
      float wave = sin(waterPosition.x * 1.4 + sin(waterPosition.y * 0.65) * 2.0 + waterTime * 0.65);
      float glint = pow(max(0.0, wave), 18.0) * pow(max(0.0, sin(waterPosition.y * 0.75 - waterTime * 0.4)), 8.0);
      float foam = smoothstep(-1.6, -0.2, ground) * (0.8 + wave * 0.2);
      diffuseColor.rgb *= 0.92 + 0.08 * sin(waterPosition.y * 0.25 + waterTime * 0.3);
      diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.9, 0.98, 0.91), max(glint * 0.45, foam * 0.82));
    `
      );
  };
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(terrain.size, terrain.size), material);
  mesh.position.z = terrain.waterLevel;

  return {
    mesh,
    animate: (seconds: number) => {
      time.value = seconds;
    },
    dispose: () => shore.dispose(),
  };
}
