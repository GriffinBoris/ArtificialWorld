import { defineStore } from "pinia";
import { computed, ref } from "vue";

export type ThemePreference = "dark" | "light";

const themeStorageKey = "app.theme";

function resolveInitialTheme(): ThemePreference {
  const storedTheme = window.localStorage.getItem(themeStorageKey);

  if (storedTheme === "dark" || storedTheme === "light") {
    return storedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyThemePreference(theme: ThemePreference) {
  const rootElement = document.documentElement;
  rootElement.dataset.theme = theme;
  rootElement.style.colorScheme = theme;
}

export const useThemeStore = defineStore("theme", () => {
  const hasInitialized = ref(false);
  const theme = ref<ThemePreference>("light");

  const isDark = computed(() => theme.value === "dark");

  function initializeTheme() {
    if (hasInitialized.value) {
      return;
    }

    const initialTheme = resolveInitialTheme();
    theme.value = initialTheme;
    applyThemePreference(initialTheme);
    hasInitialized.value = true;
  }

  function setTheme(nextTheme: ThemePreference) {
    theme.value = nextTheme;
    applyThemePreference(nextTheme);
    window.localStorage.setItem(themeStorageKey, nextTheme);
  }

  function toggleTheme() {
    setTheme(isDark.value ? "light" : "dark");
  }

  return {
    hasInitialized,
    initializeTheme,
    isDark,
    setTheme,
    theme,
    toggleTheme,
  };
});
