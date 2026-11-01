<template>
  <AppSurface
    root-class="w-full max-w-md"
    content-class="space-y-6 p-6 sm:p-8"
  >
    <PageFormHeader
      eyebrow="App"
      title="Create account"
      description="Register a new account to get started"
      :centered="true"
    />

    <AlertBanner
      v-if="errorMessage"
      :message="errorMessage"
      tone="warning"
    />

    <form
      class="space-y-4"
      @submit.prevent="void submitRegister()"
    >
      <AppTextField
        v-model="formValues.firstName"
        label="First name"
        :error="fieldErrors.firstName"
        placeholder="Alex"
        autocomplete="given-name"
      />
      <AppTextField
        v-model="formValues.lastName"
        label="Last name"
        :error="fieldErrors.lastName"
        placeholder="Morgan"
        autocomplete="family-name"
      />
      <AppTextField
        v-model="formValues.email"
        label="Email"
        type="email"
        :error="fieldErrors.email"
        placeholder="you@example.com"
        autocomplete="email"
      />
      <AppTextField
        v-model="formValues.passwordOne"
        label="Password"
        type="password"
        :error="fieldErrors.passwordOne"
        placeholder="Create password"
        autocomplete="new-password"
      />
      <AppTextField
        v-model="formValues.passwordTwo"
        label="Confirm password"
        type="password"
        :error="fieldErrors.passwordTwo"
        placeholder="Confirm password"
        autocomplete="new-password"
      />

      <div class="space-y-3 pt-2">
        <AppButton
          button-type="submit"
          label="Create account"
          tone="primary"
          root-class="w-full justify-center"
          :disabled="isSubmitting"
        />

        <AppButton
          label="Already have an account? Sign in"
          tone="link"
          root-class="w-full justify-center"
          @click="goToLogin"
        />
      </div>
    </form>
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
  import { createDefaultRegisterInput, registerInputSchema } from "@/types/auth/RegisterInputInterface";
  import { extractFirstFieldErrors, getFirstApiErrorMessage } from "@/utils/errorHandling";
  import { ref } from "vue";
  import { useRouter } from "vue-router";

  const router = useRouter();
  const authStore = useAuthStore();

  const errorMessage = ref("");
  const isSubmitting = ref(false);
  const {
    errors: fieldErrors,
    setErrors,
    validate,
    values: formValues,
  } = useSchemaValidation(registerInputSchema, createDefaultRegisterInput());

  async function submitRegister() {
    errorMessage.value = "";

    if (!(await validate())) {
      return;
    }

    isSubmitting.value = true;

    try {
      await authStore.register(formValues);
      await router.replace({ name: "home" });
    } catch (error) {
      setErrors(extractFirstFieldErrors(error));
      errorMessage.value = getFirstApiErrorMessage(error, "Unable to create your account.");
    } finally {
      isSubmitting.value = false;
    }
  }

  function goToLogin() {
    void router.push({ name: "login" });
  }
</script>
