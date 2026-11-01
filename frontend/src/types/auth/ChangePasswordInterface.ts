import { z } from "zod";

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPasswordOne: z.string().min(1, "New password is required"),
    newPasswordTwo: z.string().min(1, "Confirm new password is required"),
  })
  .refine((values) => values.newPasswordOne === values.newPasswordTwo, {
    message: "Passwords must match",
    path: ["newPasswordTwo"],
  });

export type ChangePasswordInterface = z.infer<typeof changePasswordSchema>;

export function createDefaultChangePassword(): ChangePasswordInterface {
  return {
    currentPassword: "",
    newPasswordOne: "",
    newPasswordTwo: "",
  };
}
