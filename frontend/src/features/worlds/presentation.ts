import type { Inhabitant, WorldEvent, WorldState } from "@/types/worlds/WorldInterface";

export const inhabitantColors = ["#eea080", "#a8b1e6", "#e9bb61", "#83c9ad", "#d89cba", "#84bdd5"];
export const assetUrl = (name: string) => `${import.meta.env.BASE_URL}assets/world/${name}`;

export function inhabitantColor(id: string) {
  return inhabitantColors[parseInt(id.replaceAll("-", "").slice(-4), 16) % inhabitantColors.length];
}

export function formatWorldTime(tick: number) {
  const seconds = Math.floor(tick / 60);

  return `${Math.floor(seconds / 3600)
    .toString()
    .padStart(2, "0")}:${Math.floor((seconds / 60) % 60)
    .toString()
    .padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;
}

export function formatAge(seconds: number) {
  return seconds < 3600
    ? `${Math.floor(seconds / 60)} minutes`
    : seconds < 86400
      ? `${(seconds / 3600).toFixed(1)} hours`
      : `${(seconds / 86400).toFixed(1)} days`;
}

export function activityLabel(agent: Inhabitant, running = false) {
  if (!agent.alive) return "Remembered";

  if (!agent.activity) return agent.driver === "pydantic" && running ? "Thinking…" : "Taking it all in";

  const labels: Record<string, string> = {
    walk: "Exploring",
    speak: "Having a chat",
    rest: "Resting",
    wait: "Taking a moment",
    gather: "Gathering",
    fell: "Felling a tree",
    take_seed: "Collecting seeds",
    plant: "Planting",
    uproot: "Clearing a planting spot",
    shape: "Making something",
    connect: "Building",
    eat: "Having a snack",
    drink: "Getting a drink",
    care: "Helping a friend",
    write: "Writing things down",
    program: "Making a device",
    consent: "Making a connection",
  };

  return labels[agent.activity.kind] ?? agent.activity.kind;
}

export function describeWorldEvent(event: WorldEvent, state?: WorldState | null) {
  const name = state?.inhabitants.find((agent) => agent.id === event.actorId)?.name ?? "Someone";

  switch (event.kind) {
    case "world.created":
      return "A little world began.";
    case "world.running":
      return "Life is unfolding.";
    case "world.paused":
      return "A moment to look around.";
    case "world.advanced":
      return "Another moment was saved.";
    case "activity.completed":
      if (event.data.kind === "walk" && event.data.status === "arrived") return `${name} arrived at their destination.`;

      return `${name} finished ${String(event.data.kind ?? "an activity")}.`;
    case "activity.failed":
      return `${name}: ${String(event.data.reason ?? "That did not quite work.")}`;
    case "inhabitant.born":
      return "A new little life joined the world.";
    case "inhabitant.named":
      return `${String(event.data.previousName)} ${event.data.selfChosen ? "chose the name" : "was named"} ${String(event.data.name)}.`;
    case "inhabitant.died":
      return `${name}'s life came to an end.`;
    case "memory.written":
      return `${name} remembered something.`;
    case "artifact.written":
      return `${name} wrote something down.`;
    case "program.deployed":
      return `${name} made a device.`;
    case "connection.created":
      return `${name} joined two parts.`;
    case "connection.broken":
      return "A connection gave way.";
    case "resource.gathered":
      return `${name} gathered some material.`;
    case "tree.felled":
      return `${name} felled a tree into a log.`;
    case "plant.seed_taken":
      return `${name} collected seeds or a cutting.`;
    case "plant.planted":
      return `${name} planted something new.`;
    case "plant.uprooted":
      return `${name} uprooted a plant, clearing its spot.`;
    case "resource.grown":
      return "A plant grew with sunlight, water, and soil.";
    case "resource.reseeded":
      return "A wild seedling appeared in a renewing resource area.";
    case "editor.ecology_enabled":
      return "Regrowth and renewing resource areas were enabled.";
    case "editor.intervened":
      return "The spectator changed the world.";
    case "editor.agents_configured":
      return "The inhabitants' settings changed.";
    case "message.spoken":
      return `${name}: “${String(event.data.text)}”`;
    default:
      return `${name} · ${event.kind.replaceAll(".", " ").replaceAll("_", " ")}`;
  }
}
