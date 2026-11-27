import { api } from "./client";
import type { User } from "./types";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export async function loginRequest(data: LoginRequest): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>("/auth/token/", data);
  return response.data;
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await api.get<User>("/auth/me/");
  return response.data;
}
