# Artificial World

A local artificial-world simulator with Django, SQLite, Vue, Three.js, and
headless Bullet physics. Create a bounded 3D world, watch its inhabitants, place
objects, inspect their records, and play back the recorded history.

Generated from the local `GriffinBoris/WebTemplate` template at `3c22fcd`, with
password accounts enabled and SSO disabled. Shared coding guidance comes from
`GriffinBoris/Agents#v0.1.0` through APM.

## Run locally

Prerequisites: Task, uv, Node.js 22.12+ (Node 22), nvm for the setup tasks, and
APM 0.28.0+ for agent guidance.

```sh
task setup:local
task ai:install
task local:backend:db:migrate
task local:dev
```

Open http://localhost:5173 to enter the full-screen spectator view. The first
visit creates a paused world if none exists. **Step 5 s** advances a paused world;
**Play** starts continuous advancement. The development task starts Django,
Vite, and the simulation worker. Django runs at http://localhost:8000.

New worlds contain six scripted inhabitants and make no model calls. The
scripted driver greets nearby inhabitants and walks around to demonstrate the simulation and recording.
It does not plan a civilization or manage its own survival.

Local development uses SQLite. Docker, Redis, Blender, API keys, and a `.env`
file are not required. Python's local world locks require macOS or Linux.

Site login is disabled by default for local development. All worlds in this
local database are available in the shared workspace, including worlds created
under existing accounts. Their owners are preserved. To require account login
again, restart with `WORLD_REQUIRE_LOGIN=1 task local:dev`.

## Subscription agents

Pydantic AI uses **OpenCode Go** by default. The backend reads the active Go key
through `opencode auth export opencode-go`. Credential output stays in memory.
If OpenCode is not installed, it reads the legacy local credential file instead
(`opencode-go`, or the shared `opencode` Console entry). You can instead supply
`OPENCODE_GO_API_KEY` in the server environment. Keys never enter world state,
browser responses, or decision logs. There is no automatic provider or paid API
fallback.

1. Connect OpenCode Go in the local OpenCode app, or supply its API key through
   the environment.
2. Restart local development with model access enabled:

   ```sh
   WORLD_ALLOW_LIVE_AI=1 task local:dev
   ```

3. Pause your world and open **World settings → agents → Agent settings**.
4. Select **Pydantic AI**, enter a Go model ID available to your account, and
   enable **Allow model calls in this world**.
5. Save the settings, then select **Play**.

Use the model ID without the `opencode-go/` prefix; for example,
`glm-5.3-flash`. The adapter uses Go's Chat Completions endpoint, identifies
itself as `ArtificialWorld/0.1`, and sends a stable session ID per inhabitant.
[OpenCode documents Go for coding-agent traffic](https://opencode.ai/v2/docs/console/go/#where-can-i-use-it),
so acceptance of this simulation workload is not guaranteed. This application
does not disguise its requests as coding traffic. Available model IDs and
account limits can change.

Sign-in alone does not enable inference. Both the server environment setting and
the world's setting must allow it. Subscription availability, model access, and
limits depend on your account. Live subscription inference has deliberately not
been used during verification.

The previous ChatGPT provider remains available with `WORLD_AI_PROVIDER=chatgpt`.
For that provider, run `task local:agent:login` first. Its credentials stay in
ignored `backend/temp/agent-credentials/chatgpt.json`, with directory mode
`0700` and file mode `0600`. Remove that file while the processes are stopped
to remove that provider's local sign-in.

The worker advances world time while inhabitants think independently. Each
completed decision starts its action against the current world state; a slow
model response does not freeze other inhabitants or physics. Four thinking
slots limit concurrent requests. A failed request is recorded and that inhabitant
retries after ten simulated seconds. Pausing cancels pending requests and keeps
their accepted conversation history. Restarting the worker leaves worlds paused
and marks interrupted decisions.
Set `WORLD_THINKING_SLOTS` from 1 to 16 to adjust concurrency without changing
physics timing. Inhabitants retain six recent conversation turns and a compact
journal of older experiences, plus their last shared plan. Their private context
survives worker restarts and renaming; full public turns remain in Django.
Nearby inhabitants can see whether someone is thinking, acting, idle, or dead.
Spoken messages stay in Django for their original nearby recipients, including
those still thinking. Unread messages arrive oldest first in batches of twenty.

## Watching the world

Use **Menu** in the top-left corner to create a new world or open a saved one.
Opening the menu pauses the current world. **Escape** opens the menu when no
other panel is open; inside a dialog or dropdown, Escape closes that control.
The new-world form lets you name the world, choose its seed, and start with
1–10 inhabitants. This is the founding population, not a limit on reproduction.
Saved worlds marked **Early landscape** use the older, sparser generator.
Creating a new world keeps those saved worlds and their history intact.

Drag to orbit, right-drag to pan, and scroll to zoom. WASD or the arrow keys move
the camera. **Landscape view** on the left shows the wider scenery and clouds;
**Return to clearing** brings you back to the inhabitants. The minimap jumps to
a nearby position. Space pauses or plays; F
focuses the selected inhabitant; Escape closes the current panel.

Walking follows a route around ground obstacles to the chosen destination.
The inhabitant continues that action between model decisions and receives an
arrival or failure result when it ends. The live viewer plays recorded motion
frames between server updates. **Step 5 s** also plays the recorded step, rather
than showing only its final position. Long speech bubbles scroll with the mouse
wheel or, when focused, the arrow keys, Page Up/Down, Home, and End. Clicking a
bubble opens the full conversation.

Click an inhabitant, a portrait, or a speech bubble to open their profile:

- **Chat** shows messages they said or could hear, with names and simulation times.
- **Memories** shows their stored personal memories and confidence.
- **Life** shows health, growth, stress, injury, wear, inherited repair, parents,
  and recorded events.
- **Mind** shows model session status, local observations, shared plans, tool
  calls and results, visible commentary, and chosen actions. Tool activity is
  saved while a decision is still running and polled by the inspector. This does
  not expose private model reasoning. Scripted inhabitants have no model sessions.

The profile and speech bubbles follow replay time. Follow along keeps the camera
on an inhabitant. World settings contains the object editor, agent controls,
and detailed records; the journal shows recent world events.

Select a profile tab, a speech bubble, or **Open full screen** to enter the
inhabitant reader. It has a scrolling record area, search, expandable
observations and tool results, and **Pause updates** to read without incoming
records shifting the content. This pauses the reader's updates, not world time.
**Back to world** or Escape returns to the quick profile. A focused search field
can consume the first Escape to clear its text.

The reader currently loads the latest 100 messages, memories, or life events,
and the latest 20 decisions. Search covers those loaded records. Older stored
records are retained, but this reader does not yet paginate them.

## Blender artwork

The repository includes the authored asset generator, editable Blender scene,
twelve exported GLB models, and a rendered portrait. The villager has idle,
walking, and talking clips. Models render the existing world entities; flowers
and clouds are cosmetic. Trees alternate between round crowns and pines, and
static resource models use instanced rendering. The scenery takes cues from
the local Garden Market project's groves, layered terrain, blue-green water,
and cloud fields; these models were built for Artificial World in Blender.

New worlds use landscape generation 2: clustered forests and rock outcrops,
berry bushes, fiber patches, nearby streams and ponds, and distant hills.
The default seed creates about 850 entities, with exact counts depending on
seed, world size, water, and spacing. Harvestable resources are physical
entities stored in Django, with explicit renewal rules. Shore foam and moving water highlights are visual
effects. Generation and collision sampling use the same terrain triangles.

Create a new world with **+ New world** to get the richer landscape. Existing
worlds retain their stored resource layout and generation 1 terrain, including
during replay. The renderer adds the new models and atmospheric details to both.

Runtime assets are included, so Blender is only needed to rebuild the artwork:

```sh
task local:frontend:assets
# macOS application installation:
task local:frontend:assets BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

The generator runs with Blender's Python, not the application's Python. Source
files are in `frontend/art/`; runtime models and the portrait are in
`frontend/public/assets/world/`. The assets were created for this repository
and use the repository license.

## World rules

- The default world is 1,024 m square, with terrain, water, wind, and boundaries.
- Agents have embodied needs, injury, stress, wear, growth, and inherited traits.
  Death follows condition; there is no maximum age or scheduled death.
- Two willing mature inhabitants can reproduce. Offspring have parents,
  inherited variation, and their own empty personal memory. There is no
  population cap.
- Agents gather material, carry parts, shape material without adding
  mass, join parts with breakable fixed or hinge connections, and apply forces.
  Buoyancy, drag, and a simplified thin-plate wind force allow physical experiments.
- Speech is local. Writing creates versioned documents on physical surfaces.
  Agents must approach a document to read it. Currency, laws, designs, and
  agreements can be written and shared; acceptance and enforcement are social.
- Programs use a bounded JSON instruction language. They have virtual records,
  local messages, a few sensors, and stored energy. They cannot access files,
  Python, a shell, the database, credentials, or the network.

This is a small ruleset for experiments. It does not yet model chemistry, heat,
fire, disease, crop growth, or realistic aerodynamics. Biological rates are toy
parameters: default gestation is six simulated hours and maturation is 24 hours,
with progress dependent on condition. Improving shelter, care, and resources can
improve modeled condition; describing an invention does not grant a new physical
effect. See [the design notes](docs/world-design.md).

## Renewable resources

New worlds include these rules automatically. For an existing world, pause it,
open **World settings → world → World editor**, select **Enable renewable
resources** from the Edit list, and choose **Apply edit**. This adds renewal rules
to its existing resources without replacing its terrain, people, or history.
Apply the database migrations and restart the development processes after updating.

- `fell` cuts a mature tree into a physical log. Its roots remain and can regrow.
  Gather material from the log, or reuse it through shaping and building.
- `take_seed` collects up to 1 kg of seeds or a cutting from a mature tree,
  berry bush, or fiber plant. This transfers real material from the source.
- `plant` roots held seeds or a cutting in reachable, unoccupied dry soil.
- `uproot` clears a stump or small plant and keeps it as a held transplant.
  Processing a seed/cutting through `shape` makes ordinary material instead.
- Trees regrow over about six simulated hours, berry bushes over one, and fiber
  plants over two. Paused worlds do not grow. Rates are stored with each plant.
- Designated groves, berry patches, and fiber beds naturally reseed into free
  space over time, even after clearing. Each area has a standing-resource target
  and a renewal interval, so unlimited long-term supply does not mean instant growth.
- Some quarry faces are inexhaustible. Extraction takes time and carrying ability,
  while the quarry face remains. Other rock deposits deplete and disappear.
  Water remains inexhaustible and can be drunk when within reach.

Finite harvesting, felling, planting, and shaping preserve material. Plant growth,
natural reseeding, and inexhaustible quarry extraction are explicit material inputs
and produce events. Resource areas have Django rows; plant state, inventory, and
growth clocks are stored with entities. Replay reads the recorded results and
does not regrow plants or reseed areas. The object inspector shows renewal rules;
Blender seed, sapling, and stump models show the changing state.

## History and local data

The database is `backend/core/db.sqlite3`. Django tables hold worlds, entities,
inhabitants, resource areas, connections, documents and versions, memories, programs, decisions,
events, checkpoints, and motion blocks.

Physics advances at 60 Hz. State is recorded at 10 Hz and at decision boundaries.
Compressed recordings include births, new parts, removals, joints, and body
condition. Replay reads those recordings; it does not invoke models, run programs,
or rerun physics. Checksums detect damaged recording payloads. Replay transfers
send each unchanged entity once per batch, then only its recorded changes;
the client reconstructs complete frames without recomputing the simulation.

The observer's profile and record inspector follow replay time for messages,
document versions, memories, decisions, and device records. Profiles show the
latest 100 memories, heard messages, and life events, plus 20 model sessions.
The message query scans the latest 1,000 speech events; older records remain
in Django. The timeline shows historical physical state. Inhabitants receive
only their local perception and private memory. Observer access does not grant
that knowledge to them.

History is retained without automatic pruning and will grow on disk. Stop local
development before copying the SQLite database for a complete local backup.
Checkpoints and motion blocks contain world data; the separate credential store
is not part of that history.

For a Django admin account:

```sh
task local:backend:db:superuser
```

The admin is available at http://localhost:8000/admin/.

## Checks

```sh
task local:test
task local:backend:lint
task local:build
task ai:check
```

Playwright covers login, world creation, editing, inspection, stepping, and replay:

```sh
task local:frontend:e2e:install
task local:frontend:e2e
```

## Layout

- `backend/worlds/simulation/`: physical rules, biology, perception, and bounded programs.
- `backend/worlds/services/`: persistence, action handling, recordings, and decision rounds.
- `backend/worlds/agents/`: Pydantic AI driver, local tools, and private subscription storage.
- `backend/core/`: accounts, API infrastructure, and local settings.
- `frontend/src/views/Worlds/`: spectator HUD, route store, profiles, minimap, and settings.
- `frontend/src/features/worlds/`: world API client, Three.js renderer, and asset loading.
- `frontend/art/`: Blender generator and editable source scene.
- `frontend/public/assets/world/`: exported models, animation clips, and portrait.
- `frontend/src/types/worlds/`: typed request and response contracts.
- `tasks/`: local setup, development, checks, and agent guidance commands.
- `.apm/`: editable, project-owned coding guidance.
- `apm.yml` and `apm.lock.yaml`: shared agent package and pinned resolution.

Commit source files and dependency lockfiles. Local databases, secrets,
`.idea/`, dependencies, build output, caches, and generated agent integrations
are ignored. GitHub checks use SQLite and only lint and test the application.
Backend tests disable real Pydantic AI model requests. A function-backed test
exercises the actual agent tool loop without sending a request to a provider.
