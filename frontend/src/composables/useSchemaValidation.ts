import { reactive } from "vue";
import type { ZodType } from "zod";

type FieldErrors<T extends Record<string, unknown>> = Partial<Record<keyof T, string>>;

export function useSchemaValidation<T extends Record<string, unknown>>(schema: ZodType<T>, initialValues: T) {
  const values = reactive({ ...initialValues }) as T;
  const errors = reactive({}) as FieldErrors<T>;

  function clearErrors() {
    for (const key of Object.keys(errors) as Array<keyof T>) {
      delete errors[key];
    }
  }

  function setErrors(nextErrors: FieldErrors<T>) {
    clearErrors();

    for (const [key, value] of Object.entries(nextErrors) as Array<[keyof T, string]>) {
      if (value) {
        errors[key] = value;
      }
    }
  }

  async function validate() {
    clearErrors();

    const parsedResult = schema.safeParse(values);

    if (parsedResult.success) {
      return true;
    }

    for (const issue of parsedResult.error.issues) {
      const fieldName = issue.path[0];

      if (typeof fieldName === "string" && !errors[fieldName as keyof T]) {
        errors[fieldName as keyof T] = issue.message;
      }
    }

    return false;
  }

  function reset(nextValues?: Partial<T>) {
    Object.assign(values, initialValues, nextValues);
    clearErrors();
  }

  return {
    clearErrors,
    errors,
    reset,
    setErrors,
    validate,
    values,
  };
}
