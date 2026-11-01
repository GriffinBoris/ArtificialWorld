<template>
  <AppSurface
    root-class="w-full max-w-md"
    content-class="space-y-6 p-6 sm:p-8"
  >
    <PageFormHeader
      eyebrow="App"
      title="Sign in"
      description="Access your account to continue"
      :centered="true"
    />

    <AlertBanner
      v-if="errorMessage"
      :message="errorMessage"
      tone="warning"
    />

    <form
      v-if="authStore.authMethods.passwordLogin"
      class="space-y-4"
      @submit.prevent="void submitLogin()"
    >
      <AppTextField
        v-model="formValues.email"
        label="Email"
        type="email"
        autocomplete="email"
        :error="fieldErrors.email"
        placeholder="you@example.com"
        test-id="login-email"
      />

      <AppTextField
        v-model="formValues.password"
        label="Password"
        type="password"
        autocomplete="current-password"
        :error="fieldErrors.password"
        placeholder="Enter password"
        test-id="login-password"
      />

      <div class="flex gap-3 pt-1">
        <AppButton
          label="Create account"
          root-class="min-w-0 flex-1 justify-center"
          test-id="login-create-account"
          @click="goToSignup"
        />

        <AppButton
          button-type="submit"
          label="Sign in"
          tone="primary"
          root-class="min-w-0 flex-1 justify-center"
          :disabled="isSubmitting"
          test-id="login-submit"
        />
      </div>
    </form>

    <div
      v-if="hasSSOProvider"
      class="flex items-center gap-3"
    >
      <div class="bg-line h-px flex-1" />
      <span class="text-muted text-secondary">{{ ssoDividerLabel }}</span>
      <div class="bg-line h-px flex-1" />
    </div>

    <div
      v-if="hasSSOProvider"
      class="space-y-3"
    >
      <AppButton
        v-if="authStore.authMethods.googleSso"
        :href="googleSSOUrl"
        root-class="w-full justify-center"
        test-id="login-google-sso"
      >
        <svg
          class="h-[18px] w-[18px] shrink-0"
          viewBox="0 0 18 18"
          aria-hidden="true"
        >
          <path
            fill="#4285F4"
            d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62Z"
          />
          <path
            fill="#34A853"
            d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.8.54-1.84.86-3.05.86-2.35 0-4.34-1.58-5.05-3.72H.94v2.33A9 9 0 0 0 9 18Z"
          />
          <path
            fill="#FBBC05"
            d="M3.95 10.7a5.4 5.4 0 0 1 0-3.4V4.97H.94a9 9 0 0 0 0 8.06l3.01-2.33Z"
          />
          <path
            fill="#EA4335"
            d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58A8.64 8.64 0 0 0 9 0 9 9 0 0 0 .94 4.97L3.95 7.3C4.66 5.16 6.65 3.58 9 3.58Z"
          />
        </svg>
        <span>Sign in with Google</span>
      </AppButton>

      <AppButton
        v-if="authStore.authMethods.microsoftSso"
        :href="microsoftSSOUrl"
        root-class="w-full justify-center"
        test-id="login-microsoft-sso"
      >
        <svg
          class="h-[18px] w-[18px] shrink-0"
          viewBox="0 0 23 23"
          aria-hidden="true"
        >
          <path
            fill="#f25022"
            d="M1 1h10v10H1z"
          />
          <path
            fill="#7fba00"
            d="M12 1h10v10H12z"
          />
          <path
            fill="#00a4ef"
            d="M1 12h10v10H1z"
          />
          <path
            fill="#ffb900"
            d="M12 12h10v10H12z"
          />
        </svg>
        <span>Sign in with Microsoft</span>
      </AppButton>
    </div>

    <AlertBanner
      v-if="!hasLoginMethod"
      message="Sign-in is not available right now. Contact support if you need access."
      tone="warning"
    />
  </AppSurface>
</template>

<script setup lang="ts">
  import AppTextField from "@/components/forms/AppTextField.vue";
  import PageFormHeader from "@/components/page/PageFormHeader.vue";
  import AlertBanner from "@/components/ui/AlertBanner.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppSurface from "@/components/ui/AppSurface.vue";
  import { useSchemaValidation } from "@/composables/useSchemaValidation";
  import { useAuthStore } from "@/stores/base";
  import { createDefaultLoginRequest, loginRequestSchema } from "@/types/auth/LoginRequestInterface";
  import { buildSSOLoginUrl } from "@/utils/api";
  import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { computed, ref } from "vue";
  import { useRoute, useRouter } from "vue-router";

  const route = useRoute();
  const router = useRouter();
  const authStore = useAuthStore();

  const errorMessage = ref("");
  const isSubmitting = ref(false);
  const {
    errors: fieldErrors,
    setErrors,
    validate,
    values: formValues,
  } = useSchemaValidation(loginRequestSchema, createDefaultLoginRequest());

  const redirectPath = computed(() =>
    typeof route.query.redirect === "string" && route.query.redirect.startsWith("/") ? route.query.redirect : null
  );
  const googleSSOUrl = computed(() => buildSSOLoginUrl("google", redirectPath.value));
  const microsoftSSOUrl = computed(() => buildSSOLoginUrl("microsoft", redirectPath.value));
  const hasSSOProvider = computed(() => authStore.authMethods.googleSso || authStore.authMethods.microsoftSso);
  const hasLoginMethod = computed(() => authStore.authMethods.passwordLogin || hasSSOProvider.value);
  const ssoDividerLabel = computed(() => (authStore.authMethods.passwordLogin ? "or continue with" : "Continue with"));

  const ssoErrorMessages: Record<string, string> = {
    invalid_state: "Unable to sign in with SSO. Please try again.",
    not_configured: "SSO is not configured for this environment.",
    profile_failed: "Unable to load your SSO profile. Contact support if this continues.",
    provider_denied: "The SSO provider denied the sign-in request.",
    provider_disabled: "That SSO sign-in option is not available right now.",
  };

  if (typeof route.query.sso_error === "string") {
    errorMessage.value = ssoErrorMessages[route.query.sso_error] ?? "Unable to sign in with SSO.";
  }

  async function submitLogin() {
    errorMessage.value = "";

    if (!(await validate())) {
      return;
    }

    isSubmitting.value = true;

    try {
      await authStore.login(formValues);

      if (redirectPath.value) {
        await router.replace(redirectPath.value);
      } else {
        await router.replace({ name: "home" });
      }
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to sign in.");
    } finally {
      isSubmitting.value = false;
    }
  }

  function goToSignup() {
    void router.push({ name: "signup" });
  }
</script>
