<template>
  <Card
    unstyled
    :pt="{
      root: cn('border border-line bg-surface shadow-none rounded-xl', rootClass),
      body: cn('h-full', bodyClass),
      caption: 'space-y-1',
      title: cn('text-heading-sm text-body font-semibold', titleClass),
      subtitle: cn('text-muted text-secondary', subtitleClass),
      content: cn('p-5', contentClass),
      footer: cn('px-5 pb-5', footerClass),
    }"
  >
    <template
      v-if="$slots.title"
      #title
    >
      <slot name="title" />
    </template>

    <template
      v-if="$slots.subtitle"
      #subtitle
    >
      <slot name="subtitle" />
    </template>

    <template #content>
      <slot />
    </template>

    <template
      v-if="$slots.footer"
      #footer
    >
      <slot name="footer" />
    </template>
  </Card>
</template>

<script setup lang="ts">
  import { cn } from "@/utils/className";
  import Card from "primevue/card";

  interface Props {
    bodyClass?: string;
    contentClass?: string;
    footerClass?: string;
    rootClass?: string;
    subtitleClass?: string;
    titleClass?: string;
  }

  defineProps<Props>();
</script>
