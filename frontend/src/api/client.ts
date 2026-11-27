import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import {
  AUTH_EXPIRED_EVENT,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./session";

const baseURL = import.meta.env.VITE_API_URL ?? "/api";

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<void> | null = null;

const refreshClient = axios.create({ baseURL });

export const api = axios.create({ baseURL });

function isTokenEndpoint(url: string | undefined): boolean {
  return Boolean(
    url && (url.includes("/auth/token/") || url.includes("/auth/token/refresh/")),
  );
}

async function performRefresh(): Promise<void> {
  const refresh = getRefreshToken();
  if (!refresh) {
    throw new Error("Нет refresh-токена");
  }

  const { data } = await refreshClient.post<{ access: string; refresh?: string }>(
    "/auth/token/refresh/",
    { refresh },
  );

  setAccessToken(data.access);
  if (data.refresh) {
    setRefreshToken(data.refresh);
  }
}

function refreshOnce(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token && !isTokenEndpoint(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(error);
    }

    const config = error.config as RetriableConfig | undefined;
    const status = (error as AxiosError).response?.status;

    if (
      status !== 401 ||
      !config ||
      config._retry ||
      isTokenEndpoint(config.url)
    ) {
      return Promise.reject(error);
    }

    config._retry = true;

    try {
      await refreshOnce();
      return await api(config);
    } catch (refreshError) {
      clearTokens();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
      return Promise.reject(refreshError);
    }
  },
);

export async function requestTokenRefresh(): Promise<void> {
  await refreshOnce();
}
