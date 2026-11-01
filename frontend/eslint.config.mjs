import js from "@eslint/js";
import prettierSkipFormatting from "@vue/eslint-config-prettier/skip-formatting";
import { defineConfigWithVueTs, vueTsConfigs } from "@vue/eslint-config-typescript";
import pluginVue from "eslint-plugin-vue";

export default defineConfigWithVueTs(
  {
    ignores: ["dist/**", "test-results/**", "playwright-report/**", "tailwind.config.js"],
  },
  js.configs.recommended,
  pluginVue.configs["flat/essential"],
  vueTsConfigs.recommended,
  prettierSkipFormatting,
  {
    languageOptions: {
      ecmaVersion: "latest",
    },
  },
);
