import { expect, test } from "@playwright/test";

test("the world selector arrow is clickable", async ({ page }) => {
  await page.goto("/#/worlds/");
  const selector = page.getByLabel("Selected world", { exact: true });
  await expect(selector).toBeVisible();
  const bounds = await page.locator(".world-name-pill").boundingBox();
  if (!bounds) throw new Error("World selector is missing.");
  await page.mouse.click(bounds.x + bounds.width - 14, bounds.y + bounds.height / 2);
  await expect(selector).toBeFocused();
  await page.keyboard.press("Escape");
});

test("settings dropdown choices remain clickable and keyboard accessible", async ({ page }) => {
  test.setTimeout(60000);
  await page.goto("/#/worlds/");
  await page.getByRole("button", { name: "World settings", exact: true }).click();
  await page.getByText("World editor", { exact: true }).click();
  const contrast = await page.locator(".panel-intro").evaluate((element) => {
    function luminance(color: string) {
      const values = color
        .match(/\d+/g)!
        .slice(0, 3)
        .map((channel) => {
          const value = Number(channel) / 255;
          return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
        });
      return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    }
    const foreground = luminance(getComputedStyle(element).color);
    const background = luminance(getComputedStyle(element.closest(".game-panel")!).backgroundColor);
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
  });
  expect(contrast).toBeGreaterThan(4.5);
  const select = page.locator("#edit-kind");
  expect((await page.locator(".app-select").first().boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await select.click();
  await expect(page.getByRole("option", { name: "Enable renewable resources", exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/dropdown.png" });
  await page.getByRole("option", { name: "Enable renewable resources", exact: true }).click();
  await expect(select).toContainText("Enable renewable resources");
  await select.click();
  await select.press("ArrowUp");
  await select.press("Enter");
  await expect(select).toContainText("Remove selected object");
  await select.click();
  await expect(page.getByRole("listbox")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("heading", { name: "World settings", exact: true })).toBeVisible();
});

test("the menu pauses a world, creates a populated world, and reopens a saved world", async ({ page, request }) => {
  test.setTimeout(90000);
  const backend = `http://localhost:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000"}`;
  const origin = `http://localhost:${process.env.PLAYWRIGHT_FRONTEND_PORT ?? "5173"}`;
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  test.skip(!bootstrap.local_world_access, "The saved-world setup uses local spectator access.");
  const created = await request.post(`${backend}/api/worlds/`, {
    headers: { "X-CSRFToken": bootstrap.csrf_token, Origin: origin },
    data: { name: "Early garden", configuration: { seed: 42, rules_version: 1 }, population: 6 },
  });
  expect(created.status()).toBe(201);
  const old = await created.json();
  await page.goto("/#/worlds/");
  await expect(page.getByLabel("Selected world", { exact: true })).toHaveValue(old.id);
  await page.getByTestId("toggle-world").click();
  await expect(page.getByRole("button", { name: "Pause", exact: true })).toBeVisible();
  await page.getByTestId("world-menu").click();
  const menu = page.getByRole("dialog", { name: "World menu", exact: true });
  await expect(menu).toBeVisible();
  await expect(menu.getByText(/uses an early landscape/)).toBeVisible();
  await expect
    .poll(async () => (await (await request.get(`${backend}/api/worlds/${old.id}/`)).json()).status)
    .toBe("paused");
  await expect(menu.getByTestId("menu-new-world")).toBeEnabled();
  await page.screenshot({ path: "test-results/world-menu.png" });
  await menu.getByTestId("menu-new-world").click();
  const form = page.getByRole("dialog", { name: "Create a world", exact: true });
  await expect(form).toBeVisible();
  await form.getByLabel("World name", { exact: true }).fill("More life");
  await form.getByLabel("Starting inhabitants", { exact: true }).fill("10");
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => Boolean(document.activeElement?.closest("dialog")))).toBe(true);
  await form.getByTestId("generate-world").click();
  await expect(form).toHaveCount(0);
  await expect(page.getByLabel("Selected world", { exact: true }).locator("option:checked")).toHaveText("More life");
  const newId = await page.getByLabel("Selected world", { exact: true }).inputValue();
  const populated = await (await request.get(`${backend}/api/worlds/${newId}/`)).json();
  expect(populated.state.inhabitants).toHaveLength(10);
  expect(populated.state.entities.length).toBeGreaterThan(400);
  expect(populated.configuration.allow_live_models).toBe(false);
  await page.getByTestId("world-menu").click();
  await menu.getByRole("button", { name: "Open Early garden", exact: true }).click();
  await expect(menu).toHaveCount(0);
  await expect(page.getByLabel("Selected world", { exact: true })).toHaveValue(old.id);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByTestId("world-menu").click();
  await expect(menu).toBeVisible();
  await expect(menu.getByTestId("menu-new-world")).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/world-menu-mobile.png" });
});

test("delete a world with confirmation and return to the menu", async ({ page, request }) => {
  test.setTimeout(90000);
  const backend = `http://localhost:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000"}`;
  await page.goto("/#/worlds/");
  const id = await page.getByLabel("Selected world", { exact: true }).inputValue();
  const world = await (await request.get(`${backend}/api/worlds/${id}/`)).json();
  const bootstrap = await (await request.get(`${backend}/api/user/bootstrap/`)).json();
  const other = await (
    await request.post(`${backend}/api/worlds/`, {
      headers: {
        "X-CSRFToken": bootstrap.csrf_token,
        Origin: `http://localhost:${process.env.PLAYWRIGHT_FRONTEND_PORT ?? "5173"}`,
      },
      data: { name: "Another saved world", population: 1 },
    })
  ).json();
  await page.getByTestId("world-menu").click();
  const menu = page.getByRole("dialog", { name: "World menu", exact: true });
  await menu.getByRole("button", { name: `Delete ${world.name}`, exact: true }).click();
  await menu.getByRole("button", { name: "Cancel deletion", exact: true }).click();
  expect((await request.get(`${backend}/api/worlds/${id}/`)).ok()).toBe(true);
  await menu.getByRole("button", { name: `Delete ${world.name}`, exact: true }).click();
  await menu.getByRole("button", { name: "Delete permanently", exact: true }).click();
  await expect(menu.getByRole("button", { name: `Delete ${world.name}`, exact: true })).toHaveCount(0);
  await expect.poll(async () => (await request.get(`${backend}/api/worlds/${id}/`)).status()).toBe(404);
  await expect(page.getByLabel("Selected world", { exact: true })).toHaveValue(other.id);
  await menu.getByRole("button", { name: `Delete ${other.name}`, exact: true }).click();
  await menu.getByRole("button", { name: "Delete permanently", exact: true }).click();
  await expect.poll(async () => (await request.get(`${backend}/api/worlds/${other.id}/`)).status()).toBe(404);
  await expect(menu.getByText("No saved worlds yet. Create a new beginning.")).toBeVisible();
  await menu.getByRole("button", { name: "New world", exact: true }).click();
  await page.getByLabel("World name", { exact: true }).fill("After deletion");
  await page.getByTestId("generate-world").click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByTestId("world-scene").locator("canvas")).toBeVisible();
});
