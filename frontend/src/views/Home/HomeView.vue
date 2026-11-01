<template>
  <PageHeader
    eyebrow="App"
    title="Welcome"
    description="This is a generic starter shell. Replace it with your own pages and navigation."
  >
    <template #actions>
      <AppButton
        icon="plus"
        label="New item"
        tone="primary"
      />
    </template>
  </PageHeader>

  <PageSection
    title="Getting started"
    description="The UI kit, theming, notifications, and API client are wired up and ready to build on."
  >
    <div class="flex flex-wrap items-center gap-3">
      <AppButton
        label="Primary"
        tone="primary"
      />
      <AppButton label="Secondary" />
      <AppButton
        label="Ghost"
        tone="ghost"
      />
      <AppTag
        tone="success"
        value="Ready"
      />
    </div>

    <div class="mt-4">
      <AppButton
        label="Show a notification"
        @click="notify"
      />
    </div>
  </PageSection>
</template>

<script setup lang="ts">
  import PageHeader from "@/components/page/PageHeader.vue";
  import PageSection from "@/components/page/PageSection.vue";
  import AppButton from "@/components/ui/AppButton.vue";
  import AppTag from "@/components/ui/AppTag.vue";
  import { useNotification } from "@/composables/useNotification";

  const notification = useNotification();

  function notify() {
    notification.success("It works", "Notifications are wired up through the notifications store.");
  }
</script>
