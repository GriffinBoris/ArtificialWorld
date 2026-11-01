import type { AxiosRequestConfig } from "axios";

import { camelToSnake } from "./caseConversion.ts";

export function buildParamsConfig<T>(params?: T): AxiosRequestConfig | undefined {
  if (!params) {
    return undefined;
  }

  return {
    params: camelToSnake(params),
  };
}
