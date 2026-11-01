import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { URL, fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const apiPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? process.env.VITE_API_PORT ?? "8000";
const developmentApiUrl = process.env.VITE_API_URL ?? `http://localhost:${apiPort}`;

export default defineConfig(({ mode }) => {
  const isProduction = mode === "production";

  return {
    base: isProduction ? "/static/" : "/",
    define: {
      __API_URL__: JSON.stringify(isProduction ? "" : developmentApiUrl),
    },
    plugins: [tailwindcss(), vue()],
    optimizeDeps: { include: ["primevue/select", "primevue/inputtext"] },
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    build: {
      assetsDir: "api",
    },
  };
});
