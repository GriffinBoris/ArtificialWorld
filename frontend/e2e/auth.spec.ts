import { expect, test } from "@playwright/test";

test("bootstrap selects local access or the configured login flow", async ({ page, request }) => {
  const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
  const bootstrap = await request.get(`http://localhost:${backendPort}/api/user/bootstrap/`);
  const payload = await bootstrap.json();
  if (payload.local_world_access) {
    await page.goto("/");
    await expect(page).toHaveURL(/#\/worlds\/$/);
    await expect(page.getByRole("main", { name: "Little World spectator" })).toBeVisible();
    await expect(page.getByTestId("login-email")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Log out" })).toHaveCount(0);
    await page.getByTestId("new-world").focus();
    await page.keyboard.press("Space");
    await expect(page.getByRole("dialog", { name: "Create a world" })).toBeVisible();
    await page.getByLabel("World name", { exact: true }).focus();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Play", exact: true })).toBeVisible();
    await page.goto("/#/login/");
    await expect(page).toHaveURL(/#\/worlds\/$/);
    return;
  }
  await page.goto("/#/home/");
  await expect(page).toHaveURL(/#\/login\/?\?redirect=/);

  await page.getByTestId("login-email").fill("e2e@example.com");
  await page.getByTestId("login-password").fill("Passwordpassword1!");
  await page.getByTestId("login-submit").click();

  await expect(page).toHaveURL(/#\/home\/$/);
  await expect(page.getByRole("heading", { name: "Welcome" })).toBeVisible();
  await page.goto("/#/worlds/");
  await expect(page.getByRole("main", { name: "Little World spectator" })).toBeVisible();
  await expect(page.getByTestId("world-scene").locator("canvas")).toBeVisible();
});

test("anonymous bootstrap provides CSRF for password login", async ({ request }) => {
  const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
  const response = await request.get(`http://localhost:${backendPort}/api/user/bootstrap/`);
  const payload = await response.json();

  expect(response.ok()).toBeTruthy();
  expect(payload.csrf_token).toBeTruthy();
  expect(payload.is_authenticated).toBe(false);
});
