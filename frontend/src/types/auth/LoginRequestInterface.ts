import { z } from "zod";

export const loginRequestSchema = z.object({
  email: z.string().email("Must be a valid email").min(1, "Email is required"),
  password: z.string().min(1, "Password is required"),
});

export type LoginRequestInterface = z.infer<typeof loginRequestSchema>;

export function createDefaultLoginRequest(): LoginRequestInterface {
  return {
    email: "",
    password: "",
  };
}
