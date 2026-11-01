import { expect, test } from "@playwright/test";

test("spectate a Blender world, read conversations and inspect an inhabitant through replay", async ({ page, request }) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
  const bootstrap = await request.get(`http://localhost:${backendPort}/api/user/bootstrap/`);
  const payload = await bootstrap.json();
  await page.goto("/#/worlds/");
  if (!payload.local_world_access) {
    await page.getByTestId("login-email").fill("e2e@example.com");
    await page.getByTestId("login-password").fill("Passwordpassword1!");
    await page.getByTestId("login-submit").click();
  }
  await expect(page.getByRole("main", { name: "Little World spectator" })).toBeVisible();
  await expect(page.getByTestId("new-world")).toBeVisible();
  await page.getByTestId("new-world").click();
  await page.getByLabel("World name", { exact: true }).fill("Recorded island");
  await page.getByTestId("generate-world").click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByLabel("Selected world")).toHaveValue(/.+/);
  await expect(page.getByLabel("Selected world").locator("option:checked")).toHaveText("Recorded island");
  await expect(page.getByTestId("world-scene").locator("canvas")).toBeVisible();
  await expect(page.getByRole("button", { name: "Meet Inhabitant 1", exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/game-preview.png" });
  await page.getByRole("button", { name: "Landscape view", exact: true }).click();
  await page.screenshot({ path: "test-results/landscape.png" });
  await page.getByRole("button", { name: "Return to clearing", exact: true }).click();

  await page.getByRole("button", { name: "World settings", exact: true }).click();
  await page.getByText("World editor", { exact: true }).click();
  await page.locator("#part-name").fill("A placed wooden block");
  await page.getByTestId("apply-world-edit").click();
  await page.getByTestId("show-history").click();
  await expect(page.getByTestId("world-events")).toContainText("The spectator changed the world.");
  await page.getByRole("button", { name: "Close panel" }).click();
  await page.getByTestId("step-world").click();
  await expect(page.getByRole("button", { name: /Conversation with Inhabitant/ }).first()).toBeVisible();
  await page
    .getByRole("button", { name: /Conversation with Inhabitant/ })
    .first()
    .click();
  const profile = page.getByTestId("inhabitant-profile");
  await expect(profile).toBeVisible();
  await expect(profile.getByTestId("conversation-message").first()).toBeVisible();
  await page.screenshot({ path: "test-results/inhabitant-chat.png" });
  await profile.getByRole("button", { name: "Memories", exact: true }).click();
  await expect(profile.getByText("Things they remember")).toBeVisible();
  await profile.getByRole("button", { name: "Life", exact: true }).click();
  await expect(profile.locator(".life-stats").getByText("Health", { exact: true })).toBeVisible();
  await profile.getByRole("button", { name: "Mind", exact: true }).click();
  await expect(profile.getByText(/scripted wandering routine/)).toBeVisible();
  await page.getByRole("button", { name: "Close profile" }).click();

  await page.getByTestId("toggle-replay").click();
  await expect(page.getByText("Replay · read only")).toBeVisible();
  await expect(page.getByLabel("Replay time")).toHaveValue("0");
  await expect(page.getByTestId("step-world")).toBeDisabled();
  await expect(page.getByRole("button", { name: /Conversation with Inhabitant/ })).toHaveCount(0);
  await page.getByTestId("play-recording").click();
  await expect.poll(async () => Number(await page.getByLabel("Replay time").inputValue())).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Pause replay" }).click();
  await page.getByTestId("toggle-replay").click();
  await expect(page.getByTestId("step-world")).toBeEnabled();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("show-inhabitants")).toBeVisible();
  await page.getByTestId("show-inhabitants").click();
  await expect(page.getByRole("heading", { name: "Little lives" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/game-mobile.png" });
  expect(errors).toEqual([]);
});
