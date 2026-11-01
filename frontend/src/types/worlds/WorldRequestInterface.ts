import type { Vector3Tuple } from "@/types/worlds/WorldInterface";

export interface AgentSettingsRequest {
  actorIds: string[];
  driver: "scripted" | "pydantic";
  modelName: string;
  allowLiveModels: boolean;
}

export interface NewPartRequest {
  name: string;
  material: "wood" | "stone" | "fiber" | "food";
  shape: "box" | "sphere" | "cylinder";
  dimensions: Vector3Tuple;
  position: Vector3Tuple;
  fixed: boolean;
  kind: "part" | "resource";
}

export type WorldEditRequest =
  | { kind: "ecology" }
  | { kind: "create"; part: NewPartRequest }
  | { kind: "move"; targetId: string; position: Vector3Tuple }
  | { kind: "remove"; targetId: string }
  | {
      kind: "body";
      targetId: string;
      metric: "health" | "food" | "water" | "energy" | "wear" | "injury" | "stress";
      value: number;
    };
