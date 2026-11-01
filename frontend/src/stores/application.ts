import { defineStore } from "pinia";
import { ref } from "vue";

export const useApplicationStore = defineStore("application", () => {
  const appName = ref("Artificial World");
  const isSidebarCollapsed = ref(false);

  function toggleSidebar() {
    isSidebarCollapsed.value = !isSidebarCollapsed.value;
  }

  function setSidebarCollapsed(value: boolean) {
    isSidebarCollapsed.value = value;
  }

  return {
    appName,
    isSidebarCollapsed,
    setSidebarCollapsed,
    toggleSidebar,
  };
});
