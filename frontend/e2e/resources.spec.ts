import { expect, test } from "@playwright/test";

test("collect seeds, plant a sapling and fell a tree into a persisted log and stump", async ({ request, page }) => {
  test.setTimeout(90000);
  const backend = `http://localhost:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000"}`;
  const origin = `http://localhost:${process.env.PLAYWRIGHT_FRONTEND_PORT ?? "5173"}`;
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  test.skip(!bootstrap.local_world_access, "This deterministic resource demonstration uses local spectator access.");
  const headers = { "X-CSRFToken": bootstrap.csrf_token, Origin: origin };
  const created = await request.post(`${backend}/api/worlds/`, { headers, data: { name: "A renewable beginning", configuration: { seed: 42, size: 128, wind: [0, 0, 0] }, population: 1 } });
  expect(created.status()).toBe(201);
  const world = await created.json();
  const base = `${backend}/api/worlds/${world.id}`;
  const actorId = world.state.inhabitants[0].id;
  const body = world.state.entities.find((entity: { id: string }) => entity.id === actorId);
  const originalIds = new Set(world.state.entities.map((entity: { id: string }) => entity.id));
  const placed = await request.post(`${base}/edit/`, { headers, data: { edit: { kind: "create", part: { name: "A tree to tend", kind: "resource", material: "wood", fixed: true, dimensions: [0.25, 0.25, 2], position: [body.position[0] + 1.1, body.position[1], body.position[2] - 0.9 + 1] } } } });
  expect(placed.status()).toBe(200);
  const tree = (await placed.json()).state.entities.find((entity: { id: string }) => !originalIds.has(entity.id));
  expect(tree.resource.supply).toBe("renewable");

  const seedAction = await request.post(`${base}/inhabitants/${actorId}/actions/`, { headers, data: { action: { kind: "take_seed", target_id: tree.id, amount: 0.25 } } });
  expect(seedAction.status()).toBe(202);
  let stepped = await request.post(`${base}/step/`, { headers, data: { seconds: 3 } });
  expect(stepped.status()).toBe(200);
  let state = (await stepped.json()).state;
  const seedId = state.inhabitants[0].held_ids[0];
  expect(state.entities.find((entity: { id: string }) => entity.id === seedId).kind).toBe("seed");
  const currentBody = state.entities.find((entity: { id: string }) => entity.id === actorId);
  const destination = [currentBody.position[0] - 0.8, currentBody.position[1] - 0.5, currentBody.position[2] - 0.85];
  const planting = await request.post(`${base}/inhabitants/${actorId}/actions/`, { headers, data: { action: { kind: "plant", target_id: seedId, destination } } });
  expect(planting.status()).toBe(202);
  stepped = await request.post(`${base}/step/`, { headers, data: { seconds: 3 } });
  state = (await stepped.json()).state;
  expect(state.entities.find((entity: { id: string }) => entity.id === seedId).kind).toBe("resource");

  const felling = await request.post(`${base}/inhabitants/${actorId}/actions/`, { headers, data: { action: { kind: "fell", target_id: tree.id } } });
  expect(felling.status()).toBe(202);
  stepped = await request.post(`${base}/step/`, { headers, data: { seconds: 10 } });
  expect(stepped.status()).toBe(200);
  state = (await stepped.json()).state;
  expect(state.entities.find((entity: { id: string }) => entity.id === tree.id).resource.felled_tick).not.toBeNull();
  expect(state.entities.some((entity: { kind: string; resource: { supply: string } | null }) => entity.kind === "part" && entity.resource?.supply === "finite")).toBe(true);
  const events = await (await request.get(`${base}/events/`)).json();
  expect(events.map((event: { kind: string }) => event.kind)).toEqual(expect.arrayContaining(["plant.seed_taken", "plant.planted", "tree.felled", "resource.grown"]));

  await page.goto("/#/worlds/");
  await expect(page.getByLabel("Selected world")).toHaveValue(world.id);
  await expect(page.getByRole("button", { name: "Meet Inhabitant 1", exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/resources-cycle.png" });
});
