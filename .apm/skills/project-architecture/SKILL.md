---
name: project-architecture
description: Use when working on Artificial World's Django backend, Vue frontend, local development setup, or shared agent guidance.
---

# Artificial World

Artificial World is a local Django/SQLite simulator with a Vue/Three.js observer.
The scaffold came from GriffinBoris/WebTemplate (commit 3c22fcd).

## Repository map

- `backend/core/`: Django settings, accounts, REST APIs, and shared backend types.
- `backend/worlds/simulation/`: typed state, Bullet physics, actions, biology,
  perception, lifecycle, and bounded JSON programs. Keep database access out.
  `generation.py` owns seeded populations and resource habitats; `terrain.py`
  owns the versioned height field and collision-surface sampling.
  `ecology.py` owns resource profiles, seeds, planting, felling, regrowth, and
  natural reseeding. ResourceArea rows persist typed area state; Entity JSON
  stores resource components and growth clocks.
- `backend/worlds/services/`: world transactions, scoped observations, persistence,
  documents, programs, recordings, editor operations, and agent decision rounds.
- `backend/worlds/agents/`: Pydantic AI, identity-bound local tools, typed decisions,
  and the private ChatGPT subscription credential source.
- `backend/worlds/management/commands/`: local worker and interactive sign-in.
- `frontend/src/`: Vue 3 and TypeScript application, routes, stores, and shared UI.
- `frontend/src/views/Worlds/`: immersive spectator HUD, route-local Pinia store,
  inhabitant profiles, minimap, and settings/editor/record panels.
- `frontend/src/features/worlds/`: API client, Three.js renderer, asset loading,
  cosmetic scenery, and presentation formatting.
- `frontend/art/`: Blender generator and editable source scene. Exported runtime
  assets live in `frontend/public/assets/world/`. Rebuild with
  `task local:frontend:assets BLENDER=/path/to/blender`; running the app needs no Blender.
- `frontend/src/types/worlds/`: API response and request contracts.
- `docs/world-design.md`: current simulation rules and intentional limits.
- `tasks/`: Task commands for local development, setup, and agent guidance.
- `.apm/`: repository-owned agent guidance sources. The shared package is pinned
  in `apm.yml` and `apm.lock.yaml`; generated integrations stay ignored.

## Local development

- Install dependencies: `task setup:local`.
- Apply the local SQLite migrations: `task local:backend:db:migrate`.
- Start Django, Vue, and the simulation worker: `task local:dev`.
- Backend tests: `task local:test`.
- Backend lint: `task local:backend:lint`.
- Frontend checks and build: `task local:build`.
- Browser tests: `task local:frontend:e2e` (install Chromium with
  `task local:frontend:e2e:install` first).
- Install shared agent guidance: `task ai:install` (APM 0.28.0 or newer).
- Rebuild guidance after editing `.apm/`: `task ai:generate`.
- Validate guidance: `task ai:check`.

The application runs locally using `core.settings.dev_local` and SQLite.
Django entrypoints default to these settings. Keep Task directory variables
relative to the repository root because included Taskfiles prepend their own
directory. Cloud infrastructure, containers, and deployment are outside the
current scope.

## Simulation invariants

- Django owns authoritative world state. API and model actions use the same
  validated domain rules. World views use `WorldBaseAPIView.world_queryset`
  and `get_world` to apply the selected access mode consistently.
- Local development defaults to `WORLD_REQUIRE_LOGIN=0`. This intentionally
  opens a shared local workspace with access to existing worlds. Owners stay
  unchanged; new local worlds use an inactive user with an unusable password.
  CSRF still applies to every browser mutation. `WORLD_REQUIRE_LOGIN=1` restores
  session authentication and owner scoping. General account and admin APIs keep
  their authentication requirements. The bootstrap exposes the access mode;
  initialize it before installing the Vue router.
- Mutations acquire the per-world file lock and a database transaction. The local
  worker has its own process lock. SQLite is intentional; this is not a distributed
  runner. File locks require macOS or Linux.
- Never hold a database transaction during a model request. Capture local
  observations per inhabitant and keep at most one request per inhabitant.
  services/runner.py owns asynchronous requests with WORLD_THINKING_SLOTS
  (default four, configurable from one to sixteen). Continue physics, biology,
  and ecology during inference; apply each result against current state. Reject
  results across a pause, death, conflicting activity, or changed driver/model.
  Pause cancels requests without advancing accepted context. Record model
  failures per inhabitant and retry after ten simulated seconds. Keep manual
  single-step calls bounded at decision boundaries. Close pending requests and
  the shared provider client when the runner exits.
  The legacy WorldConfig.thinking_slots field is accepted for old recordings
  but excluded from new snapshots; runner settings own the concurrency limit.
- Expose every agent action as a named Pydantic AI tool. Physical tools use
  CallDeferred and the existing activity pipeline; return real completion or
  failure through DeferredToolResults on the next decision. Keep tool call IDs
  and activity IDs in Decision.trace. Persist public message parts in
  Decision.messages and bounded per-inhabitant history in Inhabitant.agent_context,
  outside shared simulation state. Retain up to six turns and 60,000 serialized
  characters; compact older exchanges into a bounded factual journal and retain
  the last shared plan. Never persist hidden model reasoning or provider metadata.
  Resolve pending calls through their original decision even after a later failed
  or interrupted attempt. Update context only when the decision is accepted, in
  the same transaction as actions. Preserve messages that arrive during inference;
  deliver unread speech oldest first in batches of twenty and acknowledge only
  the included range after acceptance. Nearby status exposes thinking, acting,
  idle, or dead and activity kind, never another inhabitant's private plan.
  DecisionDraft is an internal scheduler record,
  never the model's output schema. Tool descriptions own action instructions.
- Complete tool traces in the same world transaction as their activity events.
  Agent-setting changes must return a failure for any activity they cancel.
  Historical profiles must hide tool results and completion ticks from the future.
- Keep age separate from condition. Do not introduce a fixed lifespan, population
  cap, magical global knowledge, or invention strings that grant physical powers.
- Finite gathering, felling, seed transfer, planting, shaping, and joining preserve
  material. Growth, natural reseeding, and inexhaustible quarry extraction are
  explicit material inputs and must be logged. Crafted material must not inherit
  living or inexhaustible source properties.
- Ecology runs on simulation ticks, never wall time or during replay. Natural
  areas have renewal intervals and standing-resource targets; individual plants
  remain removable. Existing worlds enable ecology through a paused, recorded
  editor action rather than an implicit rewrite of their history or terrain.
- New worlds use rules version 2 and denser resource habitats. Preserve version 1
  height fields for saved worlds and replay. Use `surface_height` for placement,
  locomotion contact, perception, and drinking so these match Bullet's triangles.
- Ground walking uses pathfinding.py for bounded routes and locomotion.py for
  physical steering. Persist typed waypoint progress on Activity. Keep active
  walkers awake in Bullet, replan when blocked, and distinguish actual arrival
  from timeout/failure. last_action_result belongs to the inhabitant and appears
  in the next local observation; waypoints do not require model decisions.
- Programs are a bounded simulation language. Never add host evaluation, imports,
  files, shell commands, SQL, or network capabilities to agent tools or programs.
- Record visible actions, local observations, tool outcomes, failures, and social
  artifacts. Never record credentials or hidden model reasoning.
- Persist tool progress on the current thinking Decision outside world transactions.
  Use the captured world ID and acquire its file lock before database access so
  progress writes cannot compete with physics transactions in SQLite.
  `share_plan` is optional spectator commentary, separate from local speech.
  Profiles show only the selected inhabitant's memories and heard messages.
- Optional name_self/name_child actions use the normal activity pipeline. Keep
  stable IDs, record name changes, and preserve names in replay and old messages.
  Self and parent naming can be repeated; self_named and parent_named record
  naming history rather than limiting future changes. Do not require naming
  or add naming customs to the scripted driver.
- The world route uses immersive RouterView rendering. Keep editor controls in
  its game settings panel. Render server entities with Blender models and keep
  decorative flowers, idle motion, and water ripples outside authoritative state.
  Batch fixed resources with instance-to-entity IDs, and keep clouds cosmetic.
- The world menu pauses the current world and retains saved worlds. Route-local
  GameDialog uses native modal dialogs for focus and input isolation. Keep scene
  controls disabled behind menu/create dialogs. Game shortcuts must respect
  handled events and ignore combobox, listbox, option, and editable focus.
- World selects reuse AppSelect. Its teleported popup uses game-select-overlay
  to keep the game palette outside the route DOM. Keep full control/arrow hit
  targets, readable text contrast, and touch-sized options.
- The full-screen inhabitant reader reuses WorldCharacterPanel inside GameDialog.
  Disable scene input behind it. Pause updates affects profile polling only.
  Label the loaded-record limits; searching a recent profile is not full-history
  search. Live walking follows rendered displacement, not stale stored velocity;
  replay uses deterministic clip poses without render-clock crossfades.
- useLiveWorldMotion owns live/step frame queues, timing, and invalidation.
  Display stored motion between polls; skip overdue frames rather than slowing
  world playback. World edits/status changes, world changes, replay, and disposal clear
  queued frames and invalidate in-flight motion reads. Keep bubble text
  scrollable, respect the route's speech-safe insets, and isolate scroll input
  from camera controls.
  Place speech bubbles above their speakers, avoid other bubbles and inhabitant
  screen bounds, and connect them to the speaker's head with a non-interactive
  tail. Keep name labels available when the viewport has no room for a bubble.
- Replay reads stored frames/checkpoints and never reruns inference, programs,
  or physics. Keep recordings immutable and checksum validated.
  Motion API responses contain entity deltas within each self-contained batch;
  the frontend API client reconstructs full frames before playback. Fixed
  resources can change or disappear, so delta detection must compare their data.

## AI and verification

Pydantic AI with the OpenCode Go API is the selected runner. Its fixed endpoint
and credentials are owned by worlds/agents/providers.py. OPENCODE_GO_API_KEY
overrides the local credential. With OpenCode installed, use only the scoped
`opencode auth export opencode-go` command and select its active Go credential.
Capture output in memory, enforce a timeout, and never export unrelated accounts.
If the CLI is absent, read the legacy auth.json Go/shared Console API entry.
An installed CLI's failure or missing Go account must not fall back to stale
legacy credentials. Never log or
return keys, copy the CLI configuration, or use another provider's credential.
Send an honest app user agent and a stable per-inhabitant session header. Go is
documented for coding-agent traffic; do not disguise this simulation or claim
that its usage is guaranteed. No live requests are needed for verification.
WORLD_AI_PROVIDER=chatgpt preserves the previous provider and its explicit
`task local:agent:login` flow. Native CLI adapters and containers remain outside
scope. Live inference requires both
`WORLD_ALLOW_LIVE_AI=1` and `WorldConfig.allow_live_models`, plus an explicit
model name. Do not add a paid API fallback or read unrelated CLI configuration.
The private credential source lives under ignored `backend/temp/agent-credentials/`
with directory mode 0700 and file mode 0600.

Do not make live model calls during tests. The world test fixture sets
`pydantic_ai.models.ALLOW_MODEL_REQUESTS=False`. Use fake drivers or Pydantic AI
FunctionModel for the agent loop. Keep provider responses untrusted and typed.
Run Ruff, focused pytest, frontend lint/typecheck/build, and browser checks for
the affected behavior. Browser tests use their own deterministic local database.

Follow existing core base classes and shared Vue components when extending the app.
Keep the implementation basic: use direct control flow instead of function dispatch
tables, separate logical steps with blank lines, and remove unused scaffold modules.
Do not add ordinary source comments; retain compiler directives and tool descriptions
that affect runtime behavior.
Keep secrets and generated files out of Git; retain dependency lockfiles and
repository-owned guidance sources. Edit `.apm/`, then regenerate integrations;
do not edit generated `AGENTS.md` or harness directories.
