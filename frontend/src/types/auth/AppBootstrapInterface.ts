import type { AuthMethodsInterface } from "@/types/auth/AuthMethodsInterface";

export interface AppBootstrapInterface {
  authMethods: AuthMethodsInterface;
  csrfToken: string;
  isAuthenticated: boolean;
  localWorldAccess: boolean;
}
