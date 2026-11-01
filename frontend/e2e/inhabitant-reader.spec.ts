import { expect, test } from "@playwright/test";

test("read an inhabitant in full screen, search records, inspect tools, and return to the world", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const backend = `http://localhost:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000"}`;
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  test.skip(!bootstrap.local_world_access, "The fixture uses local spectator access.");
  await page.goto("/#/worlds/");
  await page.getByTestId("new-world").click();
  await page.getByLabel("World name", { exact: true }).fill("Reader garden");
  await page.getByTestId("generate-world").click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const worldId = await page.getByLabel("Selected world", { exact: true }).inputValue();
  const world = await (await request.get(`${backend}/api/worlds/${worldId}/`)).json();
  const inhabitant = world.state.inhabitants[0];
  let profileReads = 0;
  await page.route(`**/api/worlds/${worldId}/inhabitants/${inhabitant.id}/profile/**`, async (route) => {
    profileReads++;
    const response = await route.fetch();
    const profile = await response.json();
    await route.fulfill({
      response,
      json: {
        ...profile,
        messages: Array.from({ length: 45 }, (_, index) => ({
          id: index + 1,
          sequence: index + 1,
          tick: 0,
          speaker_id: inhabitant.id,
          speaker_name: inhabitant.name,
          text: index === 0 ? "I found berries beside the stream." : `A recorded conversation, moment ${index + 1}.`,
          recipient_ids: [],
          position: profile.position,
        })),
        memories: [{ id: 1, tick: 0, text: "The stream leads to berries.", confidence: 0.9 }],
        decisions: [
          {
            id: "reader-fixture",
            tick: 0,
            status: "completed",
            observation: {
              name: inhabitant.name,
              position: profile.position,
              visible_objects: [{ id: "tree-fixture", name: "A nearby pine", kind: "resource", material: "wood" }],
            },
            trace: [
              { tool: "share_plan", arguments: { text: "I will investigate the berries." } },
              {
                tool: "inspect",
                arguments: { object_id: "tree-fixture" },
                result: { name: "A nearby pine", material: "wood" },
              },
              { tool: "walk", arguments: { destination: [5, 8, 0] }, status: "running", activity_id: "walk-fixture" },
              {
                tool: "speak",
                arguments: { text: "I found berries." },
                status: "completed",
                result: { status: "completed" },
              },
            ],
            result: { action: { kind: "walk", seconds: 3 }, message: "Heading toward the stream." },
            error: "",
          },
        ],
      },
    });
  });
  await page.getByRole("button", { name: `Inspect ${inhabitant.name}`, exact: true }).click();
  await page.getByRole("button", { name: "Open full screen", exact: true }).click();
  const reader = page.getByRole("dialog", { name: "Inhabitant details", exact: true });
  const profile = reader.getByTestId("inhabitant-profile");
  await expect(reader).toBeVisible();
  await expect(profile.getByTestId("conversation-message")).toHaveCount(45);
  const scroll = profile.locator(".profile-content");
  await scroll.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  expect(await scroll.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  const search = reader.getByRole("searchbox", { name: "Search inhabitant records" });
  await search.fill("berries");
  await expect(profile.getByTestId("conversation-message")).toHaveCount(1);
  await expect(profile.getByTestId("conversation-message")).toContainText("beside the stream");
  await search.fill("missing phrase");
  await expect(profile.getByText(/No matching records/)).toBeVisible();
  await reader.getByRole("button", { name: "Mind", exact: true }).click();
  await expect(search).toHaveValue("");
  await expect(profile.getByText("I will investigate the berries.", { exact: true })).toBeVisible();
  await expect(profile.getByText("Action in progress", { exact: true })).toBeVisible();
  await expect(profile.getByText("Action completed", { exact: true })).toBeVisible();
  await profile.getByText("What they could see", { exact: false }).click();
  await expect(profile.getByText("A nearby pine", { exact: false }).first()).toBeVisible();
  await profile.getByText("Full observation", { exact: true }).click();
  await expect(profile.locator("pre").filter({ hasText: "visibleObjects" })).toBeVisible();
  await profile.getByText("Action and outcome details", { exact: true }).click();
  await expect(profile.locator("pre").filter({ hasText: '"seconds": 3' })).toBeVisible();
  await page.screenshot({ path: "test-results/inhabitant-mind-fullscreen.png" });
  await reader.getByRole("button", { name: "Pause updates", exact: true }).click();
  const pausedReads = profileReads;
  await page.waitForTimeout(1800);
  expect(profileReads).toBe(pausedReads);
  await reader.getByRole("button", { name: "Resume updates", exact: true }).click();
  await expect.poll(() => profileReads).toBeGreaterThan(pausedReads);
  await reader.getByRole("button", { name: "Chat", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(search).toBeInViewport();
  await expect(reader.getByRole("button", { name: "Back to world", exact: true })).toBeInViewport();
  expect(await reader.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  await search.fill("berries");
  await page.keyboard.press("Space");
  expect((await (await request.get(`${backend}/api/worlds/${worldId}/`)).json()).status).toBe("paused");
  await page.screenshot({ path: "test-results/inhabitant-reader-mobile.png" });
  await reader.getByRole("button", { name: "Back to world", exact: true }).focus();
  await page.keyboard.press("Escape");
  await expect(reader).toHaveCount(0);
  await expect(page.getByTestId("inhabitant-profile")).toBeVisible();
  await page.getByRole("button", { name: "Mind", exact: true }).click();
  await expect(reader).toBeVisible();
  await reader.getByRole("button", { name: "Back to world", exact: true }).click();
  await expect(reader).toHaveCount(0);
  expect(errors).toEqual([]);
});
