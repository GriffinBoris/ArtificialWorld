import type { EmptyResponseInterface } from "@/types/api/EmptyResponseInterface";
import type { AppBootstrapInterface } from "@/types/auth/AppBootstrapInterface";
import type { ChangePasswordInterface } from "@/types/auth/ChangePasswordInterface";
import type { LoginRequestInterface } from "@/types/auth/LoginRequestInterface";
import type { RegisterInputInterface } from "@/types/auth/RegisterInputInterface";
import { camelToSnake, snakeToCamel } from "@/utils/caseConversion";
import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from "axios";

export class ApiClient {
  private axios: AxiosInstance;

  constructor(baseURL: string) {
    this.axios = axios.create({
      baseURL,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      xsrfHeaderName: "X-CSRFTOKEN",
      xsrfCookieName: "csrftoken",
      withCredentials: true,
      withXSRFToken: true,
      timeout: 60_000,
    });

    this.axios.interceptors.response.use(
      (response: AxiosResponse) => {
        response.data = snakeToCamel(response.data);

        return response;
      },
      (error: AxiosError) => {
        const data = error.response?.data;

        if (error.response && data) {
          error.response.data = snakeToCamel(data);
        }

        return Promise.reject(error);
      }
    );
  }

  setCsrfToken(token: string) {
    this.axios.defaults.headers.common["X-CSRFTOKEN"] = token;
  }

  async get<TResponse>(url: string, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.get<TResponse>(url, config);

    return data;
  }

  async post<TResponse, TBody>(url: string, body?: TBody, config?: AxiosRequestConfig): Promise<TResponse> {
    const { data } = await this.axios.post<TResponse>(url, camelToSnake(body), config);

    return data;
  }

  async delete(url: string): Promise<void> {
    await this.axios.delete(url);
  }
}

export const apiClient = new ApiClient(__API_URL__);

export type SSOProvider = "google" | "microsoft";

export function buildSSOLoginUrl(provider: SSOProvider, redirect?: string | null) {
  const apiBaseUrl = __API_URL__.replace(/\/$/, "");
  const queryParams = new URLSearchParams();

  if (redirect) {
    queryParams.set("redirect", redirect);
  }

  const queryString = queryParams.toString();

  return `${apiBaseUrl}/api/user/sso/${provider}/login/${queryString ? `?${queryString}` : ""}`;
}

const auth = {
  bootstrap: () => apiClient.get<AppBootstrapInterface>("api/user/bootstrap/"),
  changePassword: (payload: ChangePasswordInterface) =>
    apiClient.post<EmptyResponseInterface, ChangePasswordInterface>("api/user/change-password/", payload),
  login: (payload: LoginRequestInterface) =>
    apiClient.post<EmptyResponseInterface, LoginRequestInterface>("api/user/login/", payload),
  logout: () => apiClient.post<EmptyResponseInterface, undefined>("api/user/logout/"),
  register: (payload: RegisterInputInterface) =>
    apiClient.post<EmptyResponseInterface, RegisterInputInterface>("api/user/register/", payload),
};

export const api = {
  auth,
};
