import type { AnimationAction, AnimationMixer } from "three";

export class InhabitantAnimation {
  private clip = "Idle";
  private replay = false;

  constructor(
    private mixer: AnimationMixer,
    private actions: Map<string, AnimationAction>,
    private phase: number
  ) {}

  update(
    delta: number,
    state: { moving: boolean; speed: number; talking: boolean; alive: boolean; replay: boolean; seconds: number }
  ) {
    const walking = state.replay ? state.speed > 0.08 : state.moving;
    const clip = state.alive ? (walking ? "Walk" : state.talking ? "Talk" : "Idle") : "Idle";

    if (clip !== this.clip || state.replay !== this.replay) {
      const previous = this.actions.get(this.clip)!;
      const next = this.actions.get(clip)!;

      if (state.replay || this.replay) this.mixer.stopAllAction();

      previous.stopFading().stopWarping();
      next.reset().setEffectiveTimeScale(1).setEffectiveWeight(1).play();

      if (!state.replay && !this.replay) next.crossFadeFrom(previous, 0.2, false);

      this.clip = clip;
      this.replay = state.replay;
    }

    if (state.replay) {
      const action = this.actions.get(clip)!;
      action.time = (state.seconds + this.phase) % action.getClip().duration;
      this.mixer.update(0);
    } else if (state.alive) this.mixer.update(delta);
  }
}
