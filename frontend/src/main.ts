import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import Tooltip from "primevue/tooltip";
import { createApp } from "vue";

import App from "./App.vue";
import "./assets/base.css";
import router from "./router";
import { useAuthStore } from "./stores/base";
import { useThemeStore } from "./stores/theme";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(PrimeVue, { unstyled: true });
app.directive("tooltip", Tooltip);

const themeStore = useThemeStore(pinia);
themeStore.initializeTheme();

const authStore = useAuthStore(pinia);
void authStore.initializeAuth().finally(async () => {
  app.use(router);
  await router.isReady();
  app.mount("#app");
});
