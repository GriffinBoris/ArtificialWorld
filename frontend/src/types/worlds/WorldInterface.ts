export type Vector3Tuple = [number, number, number];
export type QuaternionTuple = [number, number, number, number];

export interface WorldConfiguration {
  rulesVersion: number;
  seed: number;
  size: number;
  ceiling: number;
  gravity: number;
  wind: Vector3Tuple;
  waterLevel: number;
  physicsHz: number;
  recordingHz: number;
  allowLiveModels: boolean;
}

export interface WorldEntity {
  id: string;
  name: string;
  kind: string;
  material: string;
  shape: string;
  dimensions: Vector3Tuple;
  position: Vector3Tuple;
  rotation: QuaternionTuple;
  velocity: Vector3Tuple;
  mass: number;
  fixed: boolean;
  condition: number;
  resource?: ResourceState | null;
}

export interface ResourceState {
  supply: "finite" | "renewable" | "infinite";
  capacity: number;
  matureDimensions: Vector3Tuple;
  rootMass: number;
  growthSeconds: number | null;
  lastGrowthTick: number;
  felledTick: number | null;
  areaId: string | null;
}

export interface ResourceArea {
  id: string;
  name: string;
  material: string;
  position: Vector3Tuple;
  radius: number;
  targetCount: number;
  renewalSeconds: number;
  nextSpawnTick: number;
}

export interface BodyState {
  health: number;
  food: number;
  water: number;
  energy: number;
  wear: number;
  injury: number;
  stress: number;
  growth: number;
  ageSeconds: number;
  air: number;
  repairTrait: number;
  strengthTrait: number;
  metabolismTrait: number;
}

export interface Inhabitant {
  id: string;
  name: string;
  selfNamed: boolean;
  parentNamed: boolean;
  alive: boolean;
  body: BodyState;
  driver: string;
  modelName: string;
  parents: string[];
  activity: { kind: string; endsTick: number } | null;
}

export interface WorldState {
  config: WorldConfiguration;
  tick: number;
  entities: WorldEntity[];
  inhabitants: Inhabitant[];
  joints: { id: string; entityA: string; entityB: string; kind: string }[];
  resourceAreas?: ResourceArea[];
}

export interface WorldSummary {
  id: string;
  name: string;
  tick: number;
  revision: number;
  status: string;
  error: string;
  eventSequence: number;
  configuration: WorldConfiguration;
}

export interface WorldDetail extends WorldSummary {
  state: WorldState;
}

export interface Terrain {
  size: number;
  waterLevel: number;
  heights: number[][];
}

export interface WorldEvent {
  id: number;
  sequence: number;
  tick: number;
  kind: string;
  actorId: string | null;
  subjectId: string | null;
  data: Record<string, string | number | boolean | object | null>;
}

export interface ReplayResult {
  state: WorldState;
  requestedTick: number;
  recordedTick: number;
}

export interface AgentAvailability {
  thinkingSlots: number;
  provider: "opencode-go" | "chatgpt";
  serverEnabled: boolean;
  subscriptionAuthorized: boolean;
  supportedDrivers: string[];
}

export interface RecordedMotion {
  frames: { tick: number; state: WorldState }[];
  untilTick: number;
}

export interface RecordedMotionDelta {
  untilTick: number;
  frames: {
    tick: number;
    state: Omit<WorldState, "entities">;
    changedEntities: WorldEntity[];
    removedEntityIds: string[];
  }[];
}

export interface EntityInspection {
  artifacts: {
    id: string;
    title: string;
    kind: string;
    versions: { version: number; content: string; tick: number; authorId: string | null }[];
  }[];
  memories: string[];
  decisions: {
    id: string;
    tick: number;
    status: string;
    observation: object;
    result: object | null;
    trace: object[];
    error: string;
  }[];
  programs: { artifactVersionId: number; enabled: boolean; nextTick: number; state: object }[];
}

export interface WorldMessage {
  id: number;
  sequence: number;
  tick: number;
  speakerId: string;
  speakerName: string;
  text: string;
  recipientIds: string[];
  position: Vector3Tuple;
}

export interface PersonalMemory {
  id: number;
  text: string;
  confidence: number;
  tick: number;
}

export interface ToolTrace {
  tool: string;
  status?: "pending" | "running" | "completed" | "failed" | "cancelled";
  toolCallId?: string;
  activityId?: string;
  completedTick?: number;
  arguments: {
    text?: string;
    objectId?: string;
    artifactId?: string;
    query?: string;
    source?: string;
    truncated?: boolean;
    destination?: Vector3Tuple;
    targetId?: string;
    seconds?: number;
    amount?: number;
    confidence?: number;
  };
  result?: object | string;
  error?: string;
}

export interface AgentDecision {
  id: string;
  tick: number;
  status: string;
  observation: {
    name: string;
    position: Vector3Tuple;
    visibleObjects: { id: string; name: string; material: string; kind: string }[];
  };
  result: {
    action: { kind: string; targetId?: string | null; text?: string; seconds?: number };
    message: string;
  } | null;
  trace: ToolTrace[];
  error: string;
}

export interface InhabitantProfile {
  inhabitant: Inhabitant;
  position: Vector3Tuple;
  memories: PersonalMemory[];
  messages: WorldMessage[];
  history: WorldEvent[];
  decisions: AgentDecision[];
  recordedTick: number;
}
