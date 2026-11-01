import { z } from "zod";

export const registerInputSchema = z
  .object({
    email: z.string().email("Must be a valid email").min(1, "Email is required"),
    firstName: z.string().min(1, "First name is required"),
    lastName: z.string().min(1, "Last name is required"),
    passwordOne: z.string().min(1, "Password is required"),
    passwordTwo: z.string().min(1, "Confirm password is required"),
  })
  .refine((values) => values.passwordOne === values.passwordTwo, {
    message: "Passwords must match",
    path: ["passwordTwo"],
  });

export type RegisterInputInterface = z.infer<typeof registerInputSchema>;

export function createDefaultRegisterInput(): RegisterInputInterface {
  return {
    email: "",
    firstName: "",
    lastName: "",
    passwordOne: "",
    passwordTwo: "",
  };
}
