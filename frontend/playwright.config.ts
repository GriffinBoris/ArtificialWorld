import { defineConfig, devices } from "@playwright/test";

const frontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT ?? "5173";
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://localhost:${backendPort}`;
const frontendBaseUrl = `http://localhost:${frontendPort}`;
const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_EXISTING_SERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [["html"], ["list"]] : "list",
  use: {
    baseURL: frontendBaseUrl,
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  webServer: [
    {
      command: `BACKEND_DOMAIN=${backendBaseUrl} FRONTEND_DOMAIN=${frontendBaseUrl} GOOGLE_SSO_CLIENT_ID=e2e-google GOOGLE_SSO_CLIENT_SECRET=e2e-secret MICROSOFT_SSO_CLIENT_ID=e2e-microsoft MICROSOFT_SSO_CLIENT_SECRET=e2e-secret uv run python manage.py run_e2e_server --addrport localhost:${backendPort} --settings=core.settings.e2e`,
      cwd: "../backend",
      url: `${backendBaseUrl}/api/user/bootstrap/`,
      reuseExistingServer,
      timeout: 120000,
    },
    {
      command: `npm run dev -- --host localhost --port ${frontendPort}`,
      cwd: ".",
      url: frontendBaseUrl,
      reuseExistingServer,
      timeout: 120000,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
