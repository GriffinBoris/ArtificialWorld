import type { AuthMethodsInterface } from "@/types/auth/AuthMethodsInterface";
import { createDefaultAuthMethods } from "@/types/auth/AuthMethodsInterface";
import type { ChangePasswordInterface } from "@/types/auth/ChangePasswordInterface";
import type { LoginRequestInterface } from "@/types/auth/LoginRequestInterface";
import type { RegisterInputInterface } from "@/types/auth/RegisterInputInterface";
import { api, apiClient } from "@/utils/api";
import { defineStore } from "pinia";
import { ref } from "vue";

export const useAuthStore = defineStore("auth", () => {
  const isAuthenticated = ref(false);
  const localWorldAccess = ref(false);
  const authMethods = ref<AuthMethodsInterface>(createDefaultAuthMethods());

  async function refreshBootstrap() {
    const bootstrap = await api.auth.bootstrap();
    apiClient.setCsrfToken(bootstrap.csrfToken);
    authMethods.value = bootstrap.authMethods;
    isAuthenticated.value = bootstrap.isAuthenticated;
    localWorldAccess.value = bootstrap.localWorldAccess;
  }

  async function initializeAuth() {
    try {
      await refreshBootstrap();
    } catch {
      isAuthenticated.value = false;
      localWorldAccess.value = false;
      authMethods.value = createDefaultAuthMethods();
    }
  }

  async function login(payload: LoginRequestInterface) {
    await api.auth.login(payload);
    await refreshBootstrap();
  }

  async function register(payload: RegisterInputInterface) {
    await api.auth.register(payload);
    await refreshBootstrap();
  }

  async function changePassword(payload: ChangePasswordInterface) {
    await api.auth.changePassword(payload);
  }

  async function logout() {
    try {
      await api.auth.logout();
    } finally {
      await refreshBootstrap();
    }
  }

  return {
    authMethods,
    changePassword,
    initializeAuth,
    isAuthenticated,
    localWorldAccess,
    login,
    logout,
    register,
  };
});
