import { expect, test } from "@playwright/test";

import { type SpeechBounds, placeSpeechBubble } from "../src/features/worlds/speechLayout";

const backend = `http://localhost:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000"}`;
const origin = `http://localhost:${process.env.PLAYWRIGHT_FRONTEND_PORT ?? "5173"}`;

test("live motion displays intermediate recorded frames and clears them when paused", async ({ page, request }) => {
  test.setTimeout(90000);
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  test.skip(!bootstrap.local_world_access, "The setup uses local spectator access.");
  const headers = { "X-CSRFToken": bootstrap.csrf_token, Origin: origin };
  const response = await request.post(`${backend}/api/worlds/`, {
    headers,
    data: {
      name: "Continuous movement",
      population: 1,
      configuration: { seed: 42, rules_version: 1, wind: [0, 0, 0] },
    },
  });
  expect(response.status()).toBe(201);
  const world = await response.json();
  await page.setViewportSize({ width: 800, height: 600 });
  await page.goto("/#/worlds/");
  const scene = page.getByTestId("world-scene");
  await expect(scene).toHaveAttribute("data-tick", "0");
  await expect(scene.locator("canvas")).toBeVisible();
  await page.evaluate(() => {
    const element = document.querySelector('[data-testid="world-scene"]')!;
    const history = document.createElement("output");
    history.id = "observed-world-ticks";
    history.hidden = true;
    document.body.append(history);
    new MutationObserver(() => {
      history.textContent += `${element.getAttribute("data-tick")},`;
    }).observe(element, { attributes: true, attributeFilter: ["data-tick"] });
  });
  await request.post(`${backend}/api/worlds/${world.id}/status/`, { headers, data: { status: "running" } });
  const stepped = await request.post(`${backend}/api/worlds/${world.id}/step/`, { headers, data: { seconds: 1 } });
  expect(stepped.status()).toBe(200);
  await expect
    .poll(async () => {
      const ticks = (await page.locator("#observed-world-ticks").textContent())!.split(",").filter(Boolean).map(Number);
      return new Set(ticks.filter((tick) => tick > 0 && tick < 60)).size;
    })
    .toBeGreaterThan(0);
  await page.getByTestId("toggle-world").click();
  await expect(page.getByRole("button", { name: "Play", exact: true })).toBeVisible();
  await expect(scene).toHaveAttribute("data-tick", "60");
  await page.locator("#observed-world-ticks").evaluate((element) => {
    element.textContent = "";
  });
  await page.waitForTimeout(500);
  await expect(scene).toHaveAttribute("data-tick", "60");
  const later = (await page.locator("#observed-world-ticks").textContent())!.split(",").filter(Boolean).map(Number);
  expect(later.every((tick) => tick === 60)).toBe(true);
  await page.getByTestId("step-world").click();
  await expect(scene).toHaveAttribute("data-tick", "360", { timeout: 15000 });
  const steppedTicks = (await page.locator("#observed-world-ticks").textContent())!
    .split(",")
    .filter(Boolean)
    .map(Number);
  expect(new Set(steppedTicks.filter((tick) => tick > 150 && tick < 300)).size).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "Play", exact: true })).toBeVisible();
});

test("speech bubbles fit short speech and scroll long speech without moving the camera", async ({ page, request }) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  test.skip(!bootstrap.local_world_access, "The setup uses local spectator access.");
  const headers = { "X-CSRFToken": bootstrap.csrf_token, Origin: origin };
  const response = await request.post(`${backend}/api/worlds/`, {
    headers,
    data: { name: "A longer conversation", population: 1, configuration: { seed: 42, wind: [0, 0, 0] } },
  });
  expect(response.status()).toBe(201);
  const world = await response.json();
  const actor = world.state.inhabitants[0];
  const actions = `${backend}/api/worlds/${world.id}/inhabitants/${actor.id}/actions/`;
  expect(
    (
      await request.post(actions, { headers, data: { action: { kind: "speak", text: "Hello!", seconds: 0.1 } } })
    ).status()
  ).toBe(202);
  expect(
    (await request.post(`${backend}/api/worlds/${world.id}/step/`, { headers, data: { seconds: 1 } })).status()
  ).toBe(200);
  await page.goto("/#/worlds/");
  const bubble = page.getByRole("button", { name: `Conversation with ${actor.name}`, exact: true });
  await expect(bubble).toBeVisible();
  const shortHeight = (await bubble.boundingBox())!.height;
  const text = Array.from(
    { length: 15 },
    (_, index) => `Line ${index + 1}: There are berries beside the stream, and a path through the trees.`
  ).join("\n");
  expect(
    (await request.post(actions, { headers, data: { action: { kind: "speak", text, seconds: 0.1 } } })).status()
  ).toBe(202);
  expect(
    (await request.post(`${backend}/api/worlds/${world.id}/step/`, { headers, data: { seconds: 1 } })).status()
  ).toBe(200);
  await expect(bubble).toContainText("Line 15:");
  const dimensions = await bubble.evaluate((element) => ({
    height: element.getBoundingClientRect().height,
    scroll: element.scrollHeight,
    client: element.clientHeight,
  }));
  expect(dimensions.height).toBeGreaterThan(shortHeight + 30);
  expect(dimensions.height).toBeLessThanOrEqual(162);
  expect(dimensions.scroll).toBeGreaterThan(dimensions.client);
  await bubble.hover();
  const before = (await bubble.boundingBox())!;
  await page.mouse.wheel(0, 180);
  await expect.poll(() => bubble.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  const after = (await bubble.boundingBox())!;
  expect(Math.abs(before.x - after.x)).toBeLessThan(2);
  expect(Math.abs(before.y - after.y)).toBeLessThan(2);
  await bubble.focus();
  await bubble.press("End");
  expect(
    await bubble.evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)
  ).toBeLessThan(2);
  await bubble.press("Home");
  expect(await bubble.evaluate((element) => element.scrollTop)).toBe(0);
  await page.screenshot({ path: "test-results/scrollable-speech.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(bubble).toBeVisible();
  const railBounds = (await page.getByRole("navigation", { name: "Spectator tools" }).boundingBox())!;
  await expect
    .poll(async () => {
      const bounds = await bubble.boundingBox();
      return (
        bounds !== null &&
        bounds.width <= 200 &&
        bounds.x > railBounds.x + railBounds.width &&
        bounds.x + bounds.width < 390
      );
    })
    .toBe(true);
  await page.screenshot({ path: "test-results/scrollable-speech-mobile.png" });
  await bubble.click();
  const reader = page.getByRole("dialog", { name: "Inhabitant details", exact: true });
  await expect(reader).toBeVisible();
  await expect(reader.getByTestId("conversation-message").filter({ hasText: "Line 15:" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("crowded bubbles find separate positions and decline space that is full", () => {
  const viewport = { x: 84, y: 86, width: 290, height: 520 };
  const placed: SpeechBounds[] = [];
  for (let index = 0; index < 4; index++) {
    const bubble = placeSpeechBubble({ x: 170, y: 206, width: 190, height: 110 }, viewport, placed);
    expect(bubble).toBeDefined();
    expect(bubble!.x).toBeGreaterThanOrEqual(viewport.x);
    expect(bubble!.y).toBeGreaterThanOrEqual(viewport.y);
    expect(bubble!.x + bubble!.width).toBeLessThanOrEqual(viewport.x + viewport.width);
    expect(bubble!.y + bubble!.height).toBeLessThanOrEqual(viewport.y + viewport.height);
    for (const other of placed) {
      expect(
        bubble!.x + bubble!.width <= other.x ||
          other.x + other.width <= bubble!.x ||
          bubble!.y + bubble!.height <= other.y ||
          other.y + other.height <= bubble!.y
      ).toBe(true);
    }
    placed.push(bubble!);
  }
  expect(placeSpeechBubble({ x: 170, y: 206, width: 190, height: 110 }, viewport, placed)).toBeUndefined();
});

test("nearby speakers have separate bubbles and tails on desktop and mobile", async ({ page, request }) => {
  test.setTimeout(90000);
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  const headers = { "X-CSRFToken": bootstrap.csrf_token, Origin: origin };
  const world = await (
    await request.post(`${backend}/api/worlds/`, { headers, data: { name: "Talking together", population: 3 } })
  ).json();
  for (const actor of world.state.inhabitants) {
    expect(
      (
        await request.post(`${backend}/api/worlds/${world.id}/inhabitants/${actor.id}/actions/`, {
          headers,
          data: {
            action: {
              kind: "speak",
              text: `Hello from ${actor.name}! There are berries by the stream. Shall we explore together?`,
              seconds: 0.1,
            },
          },
        })
      ).status()
    ).toBe(202);
  }
  expect(
    (await request.post(`${backend}/api/worlds/${world.id}/step/`, { headers, data: { seconds: 1 } })).status()
  ).toBe(200);
  await page.goto("/#/worlds/");
  const bubbles = page.locator(".speech-bubble");
  await expect(bubbles).toHaveCount(3);
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await page.screenshot({ path: `test-results/separated-speech-${width}.png` });
    await expect
      .poll(async () => {
        const boxes = await bubbles.evaluateAll((elements) =>
          elements.map((element) => {
            const box = element.getBoundingClientRect();
            return {
              x: box.x,
              y: box.y,
              right: box.right,
              bottom: box.bottom,
              visible: getComputedStyle(element).visibility === "visible",
              personTop: element.parentElement!.getBoundingClientRect().top,
            };
          })
        );
        const visible = boxes.filter((box) => box.visible && box.right > box.x);
        if (visible.length < (width === 1280 ? 3 : 1)) return [{ missing: true, boxes }];
        return visible.filter(
          (box, index) =>
            !(
              box.bottom <= box.personTop - 8 &&
              box.x >= 83 &&
              box.right <= width + 1 &&
              box.y >= 85 &&
              visible
                .slice(index + 1)
                .every(
                  (other) =>
                    box.right <= other.x || other.right <= box.x || box.bottom <= other.y || other.bottom <= box.y
                )
            )
        );
      })
      .toEqual([]);
    await expect(page.locator(".speech-tails path")).toHaveCount(3);
    await page.screenshot({ path: `test-results/separated-speech-${width}.png` });
  }
});
