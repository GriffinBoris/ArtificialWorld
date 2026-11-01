import type {
  AgentAvailability,
  EntityInspection,
  InhabitantProfile,
  RecordedMotion,
  RecordedMotionDelta,
  ReplayResult,
  Terrain,
  WorldDetail,
  WorldEntity,
  WorldEvent,
  WorldMessage,
  WorldSummary,
} from "@/types/worlds/WorldInterface";
import type { AgentSettingsRequest, WorldEditRequest } from "@/types/worlds/WorldRequestInterface";
import { apiClient } from "@/utils/api";
import { buildParamsConfig } from "@/utils/apiParams";

export const worldsApi = {
  delete: (id: string) => apiClient.delete(`api/worlds/${id}/`),
  list: () => apiClient.get<WorldSummary[]>("api/worlds/"),
  create: (name: string, seed: number, population: number) =>
    apiClient.post<WorldDetail, { name: string; configuration: { seed: number }; population: number }>("api/worlds/", {
      name,
      configuration: { seed },
      population,
    }),
  detail: (id: string) => apiClient.get<WorldDetail>(`api/worlds/${id}/`),
  terrain: (id: string) => apiClient.get<Terrain>(`api/worlds/${id}/terrain/`),
  events: (id: string, after: number) =>
    apiClient.get<WorldEvent[]>(`api/worlds/${id}/events/`, buildParamsConfig({ after })),
  step: (id: string) => apiClient.post<WorldDetail, { seconds: number }>(`api/worlds/${id}/step/`, { seconds: 5 }),
  status: (id: string, status: "running" | "paused") =>
    apiClient.post<WorldSummary, { status: string }>(`api/worlds/${id}/status/`, { status }),
  replay: (id: string, tick: number) =>
    apiClient.get<ReplayResult>(`api/worlds/${id}/replay/`, buildParamsConfig({ tick })),
  async motion(id: string, after: number): Promise<RecordedMotion> {
    const recording = await apiClient.get<RecordedMotionDelta>(
      `api/worlds/${id}/motion/`,
      buildParamsConfig({ after })
    );
    const entities = new Map<string, WorldEntity>();

    return {
      untilTick: recording.untilTick,
      frames: recording.frames.map((frame) => {
        frame.removedEntityIds.forEach((identity) => entities.delete(identity));
        frame.changedEntities.forEach((entity) => entities.set(entity.id, entity));

        return { tick: frame.tick, state: { ...frame.state, entities: [...entities.values()] } };
      }),
    };
  },
  agentAvailability: (id: string) => apiClient.get<AgentAvailability>(`api/worlds/${id}/agent-settings/`),
  configureAgents: (id: string, request: AgentSettingsRequest) =>
    apiClient.post<WorldDetail, AgentSettingsRequest>(`api/worlds/${id}/agent-settings/`, request),
  edit: (id: string, edit: WorldEditRequest) =>
    apiClient.post<WorldDetail, { edit: WorldEditRequest }>(`api/worlds/${id}/edit/`, { edit }),
  inspect: (id: string, entityId: string, tick: number | null = null) =>
    apiClient.get<EntityInspection>(
      `api/worlds/${id}/inspect/${entityId}/`,
      tick === null ? undefined : buildParamsConfig({ tick })
    ),
  messages: (id: string, tick: number | null = null) =>
    apiClient.get<WorldMessage[]>(
      `api/worlds/${id}/messages/`,
      tick === null ? undefined : buildParamsConfig({ tick })
    ),
  profile: (id: string, actorId: string, tick: number | null = null) =>
    apiClient.get<InhabitantProfile>(
      `api/worlds/${id}/inhabitants/${actorId}/profile/`,
      tick === null ? undefined : buildParamsConfig({ tick })
    ),
};
