import "vue-router";

declare module "vue-router" {
  interface RouteMeta {
    guestOnly?: boolean;
    requiresAuth?: boolean;
    title?: string;
  }
}

export {};
