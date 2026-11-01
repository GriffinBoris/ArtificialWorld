import { expect, test } from "@playwright/test";
import { AnimationClip, AnimationMixer, NumberKeyframeTrack, Object3D } from "three";

import { InhabitantAnimation } from "../src/features/worlds/InhabitantAnimation";

function rig() {
  const root = new Object3D();
  const mixer = new AnimationMixer(root);
  const actions = new Map([
    ["Idle", mixer.clipAction(new AnimationClip("Idle", 1, [new NumberKeyframeTrack(".rotation[x]", [0, 1], [0.1, 0.2])]))],
    ["Walk", mixer.clipAction(new AnimationClip("Walk", 1, [new NumberKeyframeTrack(".rotation[x]", [0, 1], [0.8, 1.2])]))],
    ["Talk", mixer.clipAction(new AnimationClip("Talk", 1, [new NumberKeyframeTrack(".rotation[x]", [0, 1], [-0.6, -0.3])]))],
  ]);
  actions.get("Idle")!.play();
  return { root, actions, animation: new InhabitantAnimation(mixer, actions, 0) };
}

test("walking returns to idle and repeated transitions keep their weight", () => {
  const { root, actions, animation } = rig();
  for (let cycle = 0; cycle < 4; cycle++) {
    animation.update(0.3, { moving: true, speed: 1, talking: false, alive: true, replay: false, seconds: 0 });
    expect(actions.get("Walk")!.getEffectiveWeight()).toBe(1);
    expect(root.rotation.x).toBeGreaterThan(0.8);
    animation.update(0.3, { moving: false, speed: 1, talking: false, alive: true, replay: false, seconds: 0 });
    expect(actions.get("Idle")!.getEffectiveWeight()).toBe(1);
    expect(root.rotation.x).toBeLessThan(0.21);
  }
});

test("replay poses survive transitions, pause, backward seeks, and return to live", () => {
  const { root, actions, animation } = rig();
  animation.update(0.05, { moving: true, speed: 1, talking: false, alive: true, replay: false, seconds: 0 });
  animation.update(0, { moving: true, speed: 1, talking: false, alive: true, replay: true, seconds: 7.4 });
  expect(root.rotation.x).toBeCloseTo(0.96);
  for (let frame = 0; frame < 30; frame++) animation.update(0.05, { moving: true, speed: 1, talking: false, alive: true, replay: true, seconds: 7.4 });
  expect(root.rotation.x).toBeCloseTo(0.96);
  animation.update(0, { moving: false, speed: 0, talking: true, alive: true, replay: true, seconds: 2.5 });
  expect(actions.get("Talk")!.getEffectiveWeight()).toBe(1);
  expect(root.rotation.x).toBeCloseTo(-0.45);
  animation.update(0, { moving: true, speed: 1, talking: false, alive: true, replay: true, seconds: 0.2 });
  expect(root.rotation.x).toBeCloseTo(0.88);
  animation.update(0.3, { moving: false, speed: 1, talking: false, alive: true, replay: false, seconds: 0.2 });
  expect(root.rotation.x).toBeLessThan(0.21);
  animation.update(0.3, { moving: true, speed: 1, talking: false, alive: true, replay: false, seconds: 0.2 });
  expect(root.rotation.x).toBeGreaterThan(0.8);
});
