import type { ErrorResponseInterface } from "@/types/api/ErrorResponseInterface";
import { snakeFieldAttrToCamel } from "@/utils/caseConversion";

interface ApiErrorShape {
  response?: {
    data?: unknown;
    status?: number;
  };
}

export type FieldErrors = Record<string, string[]>;
export type FirstFieldErrors = Record<string, string>;

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function isErrorItem(value: unknown) {
  return (
    isObject(value) &&
    typeof value.detail === "string" &&
    (value.attr === undefined || typeof value.attr === "string") &&
    (value.code === undefined || typeof value.code === "string")
  );
}

export function isApiError(error: unknown): error is ApiErrorShape {
  if (!isObject(error)) {
    return false;
  }

  return error.response === undefined || isObject(error.response);
}

export function isStandardizedErrorResponse(data: unknown): data is ErrorResponseInterface {
  return isObject(data) && Array.isArray(data.errors) && data.errors.every(isErrorItem);
}

export function parseApiError(error: unknown): ErrorResponseInterface | null {
  if (!isApiError(error)) {
    return null;
  }

  const data = error.response?.data;

  if (!isStandardizedErrorResponse(data)) {
    return null;
  }

  return data;
}

export function extractFieldErrors(error: unknown): FieldErrors {
  const fieldErrors: FieldErrors = {};
  const errorResponse = parseApiError(error);

  if (!errorResponse?.errors) {
    return fieldErrors;
  }

  for (const errorItem of errorResponse.errors) {
    if (!errorItem.attr) {
      continue;
    }

    const normalizedAttr = snakeFieldAttrToCamel(errorItem.attr);
    const messages = fieldErrors[normalizedAttr] ?? [];
    messages.push(errorItem.detail);
    fieldErrors[normalizedAttr] = messages;
  }

  return fieldErrors;
}

export function extractFirstFieldErrors(error: unknown): FirstFieldErrors {
  const firstFieldErrors: FirstFieldErrors = {};
  const fieldErrors = extractFieldErrors(error);

  for (const [key, values] of Object.entries(fieldErrors)) {
    const firstMessage = values[0];

    if (firstMessage) {
      firstFieldErrors[key] = firstMessage;
    }
  }

  return firstFieldErrors;
}

export function getApiErrorStatus(error: unknown): number | null {
  if (!isApiError(error)) {
    return null;
  }

  return typeof error.response?.status === "number" ? error.response.status : null;
}

export function getFirstApiErrorCode(error: unknown): string | null {
  return parseApiError(error)?.errors?.[0]?.code ?? null;
}

export function getFirstApiErrorMessage(error: unknown, fallbackMessage: string): string {
  const errorResponse = parseApiError(error);
  const firstError = errorResponse?.errors?.[0];

  return firstError?.detail || fallbackMessage;
}
