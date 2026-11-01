# World design

The world has simple stable rules. Inhabitants can combine what exists and
observe the consequences. The backend validates actions and owns physical
state. A model proposes actions; it does not write state or define new rules.

## Time and decisions

World time uses integer ticks at 60 ticks per simulated second. A local worker
advances running worlds while inhabitants think independently. Model requests
happen outside database transactions. Each idle inhabitant receives its own
local observation when a thinking slot is available. Four thinking slots limit concurrent
requests independently of population. Set WORLD_THINKING_SLOTS from 1 to 16 to
change this local runner limit. Physics and recording frequencies do not change.

Completed decisions start their actions against current world state. Resource
contention follows action completion order; model latency can affect who acts
first. A changed target can cause an ordinary tool failure. Physics, biology,
ecology, and other inhabitants continue during inference. Long activities do
not require a model request on each physics tick. Manual single-step requests
retain a bounded decision boundary for inspecting paused worlds.

Local observations show visible inhabitants as thinking, acting, idle, or dead,
with the kind of their current activity. Private plans remain private. Speech
records its nearby recipients when spoken and stays available even while they
think or move away. Unread messages arrive oldest first, twenty per observation;
the read cursor advances only through messages included in an accepted turn.

A walk action selects a destination area, then follows a persisted route on the
ground. A bounded A* search accounts for body clearance, object bounds, terrain
slopes, deep water, and world boundaries. Destination x/y selects the area;
elevation follows the terrain rather than the requested z value. Route smoothing
removes unnecessary grid turns. Bullet moves the body with limited ground forces; it is not moved
from waypoint to waypoint by teleportation. Walking keeps the body awake.
If progress stops, the controller can replan around changed obstacles. It reports
failure when it cannot find a route, remains blocked, or exceeds the journey's
time allowance. A timeout is not reported as arrival.

The agent stays busy for the whole action. Its next observation includes
`last_action_result`: arrival or failure, position, and the applicable outcome
details. Successful walks include the requested destination and elapsed time.
World actions are named Pydantic AI tools, including `walk`, `speak`, `gather`,
and `plant`. A call pauses the model turn while the simulator completes the
activity. The next turn receives the actual result under the same tool call ID.
Each inhabitant retains its own public conversation and tool history in Django.
The runner carries up to six recent turns, limited to 60,000 serialized characters.
Older exchanges become an abridged factual journal with up to 24 entries and
6,000 characters. The last shared plan survives compaction. This journal does not
invent conclusions or replace long-term memories. Complete public turns remain
on the original decision records; hidden model reasoning and provider metadata
are never stored. Existing inhabitants seed their context from their own records.
Session IDs remain tied to inhabitant IDs across renaming, pauses, and restarts.
Failed or stale decisions do not advance conversations, and a later retry resolves
the last accepted action through its original tool call ID.
`remember` records memories through a tool rather than a final response field.
Waypoint progress survives server steps and state reloads. This is ground
navigation; it does not yet plan climbing or routes over constructed platforms.

Each round records its observation, validated result, world-tool trace, and
status. During inference, tools persist their progress in the decision row.
The optional `share_plan` tool publishes short intentions or observations to
the spectator, without speaking to other inhabitants. It does not store hidden
model reasoning. Pausing cancels pending requests. A result from before a pause
is rejected even after resuming; an ordinary physics tick does not invalidate it.
The inhabitant must still be alive, idle, and configured for the same model.
Failed provider requests do not apply partial actions or stop other inhabitants;
the failed inhabitant retries after ten simulated seconds.

## Bodies and population

Inhabitants have food, water, energy, health, injury, stress, wear, growth, age,
and a few inherited traits. Age is elapsed lived time. It is not a death timer.
Nutrition and rest support repair; unmet needs and injury reduce condition.
Wear reflects strain minus repair. A well-supported body can avoid net wear.

Reproduction requires two distinct living mature inhabitants in reach, with
matching consent and sufficient condition. Consent can be withdrawn before
conception. Gestation and growth depend on nourishment and condition.
Children receive new identities and no parental personal memories. They can
learn through local messages and physical documents.

Naming is optional and repeatable. `name_self` changes the actor's own name using
`text`. `name_child` changes the name of the actor's child using `target_id`
and `text`. Either parent or the child can change that name again.
The self_named and parent_named flags record past naming, not remaining choices.
Names may be shared and have no required cultural
format. IDs, relationships, and old messages remain intact. Each successful
choice records `inhabitant.named` with the previous and new names, and replay
preserves historical names. These are actions available to agents, not required
steps or scripted naming behavior.

There is no population ceiling. Material, care, space, and the cost of running
decisions constrain growth. The initial population selector limits only the
number of founders created by that request. Default gestation and maturation
rates are convenient experimental settings, not a human biology model.

## Matter and invention

New worlds use generation 2, with seeded forest groves, varied resource sizes,
rock clusters, berry bushes, fiber patches, streams, ponds, and hills. Resources
remain physical entities with finite, renewable, or inexhaustible supply rules. The starting clearing stays open and has nearby
resources and water. Positions stay inside the selected world bounds.

The saved configuration's `rules_version` selects the terrain generator.
Generation 1 worlds keep their original height field and 64-cell grid; generation
2 uses a 128-cell grid. Physics, placement, perception, and drinking sample that
same collision surface. Rendering consumes the server grid rather than a second
terrain generator. Existing worlds and recordings are not regenerated.

Parts have shape, dimensions, mass, material, pose, velocity, and condition.
The initial materials are wood, stone, fiber, food, and bodies. Gathering
subtracts mass from a deposit. Shaping preserves material as the new part and
offcuts. Joining transfers binding fiber into the assembly.

Living resource entities store their mature dimensions, capacity, root reserve,
growth time, and last growth tick. Gathering leaves their roots intact. Felling
transfers a tree's harvestable mass into a loose physical log; roots regrow unless
uprooted. Seeds and cuttings transfer material from a mature plant and become a
new rooted plant through a validated planting action. Uprooting allows clearing
and transplantation. Shaping plant material removes its propagation properties.

Default full-growth times are six simulated hours for trees, one for berry
bushes, and two for fiber. Growth adds material from an abstract sunlight, water,
and soil supply; this is an explicit environmental input, not chemical simulation.
Growth uses simulation ticks and stops when the world is paused.

Designated resource areas naturally reseed into available dry ground at stored
intervals, up to a standing-resource target. Individual plants can still be
removed. These areas provide unlimited long-term biological supply with finite
growth and emergence rates. Some quarry faces are inexhaustible; their visible
mass remains while extraction adds new stone. Ordinary deposits stay finite.
Water is an inexhaustible level surface. Growth, reseeding, and quarry inputs are
logged separately from transfers so material accounting remains explicit.

Resource areas live in Django rows; resource components and growth clocks live
in entity state. Checkpoints and motion frames include both. Existing worlds can
enable ecology through a paused editor intervention, preserving their layout and
earlier records. Replay does not execute growth or reseeding.

Bullet handles collisions and constrained rigid bodies. Fixed connections keep
relative orientation; hinges allow rotation around a shared axis. Forces at an
off-center contact point produce torque. Connections can break under load.
Simplified buoyancy and wind forces support experiments with floats, levers,
structures, and plates. These laws are deliberately approximate.

There is no invention endpoint that grants arbitrary effects. An inhabitant can
create a design document, make parts, test them, and record observations.
Model knowledge is not erased: a language model can already know concepts such
as buoyancy or currency. The simulation controls what it observes and can do.

## Ideas, communication, and institutions

Documents have authors, physical locations, and versions. Speech has a position
and a recorded recipient list. A private memory belongs to one inhabitant.
There is no shared archive automatically injected into every prompt.

An inhabitant can name a currency, propose a law, keep a ledger, or record a
contract using ordinary writing. Other inhabitants can read, copy, discuss,
accept, or ignore it. A document does not create backend ownership rights or
automatic enforcement. Physical possession is represented by grasp connections.
Trade can use physical transfers and communicated agreements.

## Programs

Programs run a small JSON language with explicit operations. Private scratch
supports calculation during a decision. A persistent device runs on a held
manufactured part after a `program` action. It stores virtual records and can
send local messages. Nearby devices and inhabitants can receive them.

Example counter:

```json
[
  {"put": "count", "value": {"op": "add", "args": [{"record": "count"}, 1]}},
  {"send": {"op": "concat", "args": ["Count: ", {"record": "count"}]}}
]
```

Available statements are `put`/`value`, `send`, `if`/`then`/`else`, and
`repeat`/`do`. Expressions include literals, record lookup, granted sensors,
and a small set of arithmetic, comparison, string, and collection operations.
Devices receive only `tick`, `name`, and their local `inbox` as sensors.

Each execution has a 256-instruction budget, 4 KB of record storage, bounded
nesting, bounded numbers, and message limits. Creating a device transfers body
energy into a finite device supply. Execution consumes that supply. The
interpreter does not evaluate host code, import modules, read files, issue
requests, or call the database. Adding a new operation requires a backend rule
and boundary tests.

## Persistence and observation

Typed state lives in Django rows; events explain changes. Compressed state
frames record motion and conditions. Immutable checkpoints identify their tick
and event sequence. Replay selects stored state rather than recomputing it.

The Vue client is a full-screen Three.js spectator with Blender characters and
scenery, world-anchored speech bubbles, and an inhabitant profile. The profile
reads personal memories, heard conversations, body condition, history, and model
sessions from Django. Polling shows shared plans and tools during a decision.
These observer records do not add knowledge to any inhabitant's prompt.
The live viewer buffers recorded motion and displays intermediate frames at
their recorded pace, including manual steps. It skips overdue display frames
when rendering cannot keep up. Pausing, editing, changing worlds, entering
replay, or leaving the route clears pending live playback. No client motion
advances authoritative state. Speech bubbles fit their content up to a maximum
height, then scroll. Horizontal placement keeps them inside the viewport and
away from the spectator rail; keyboard and wheel scrolling stay in the bubble.
The displayed models and animations are cosmetic; Bullet still owns collisions.
Static resource models are instanced, with instance selection mapped back to
their real entity IDs. Decorative wildflowers and clouds have no material or
tool capabilities. Water highlights and shore foam do not change water physics.

Site login is disabled by default,
and local access includes existing worlds without changing their owners.
`WORLD_REQUIRE_LOGIN=1` restores session authentication and owner scoping.
Editing requires a paused
world and produces an intervention event and checkpoint. Agent tools receive
an identity-bound local snapshot. Inspection, memories, documents, calculations,
plans, and all world actions use named tools. Tool arguments use the same
validated action rules as the API. Agents do not return an action object in
a final response. These are direct Pydantic AI tools; no MCP server is needed.

Current limits include abstract plant growth without nutrient depletion or seasons, approximate force and
biology models, approximate collision shapes, and one local simulation worker. Better
ecology, richer experiments, new physical effects, and rendering detail can be
added as verified rules without turning social ideas into hardcoded game systems.
