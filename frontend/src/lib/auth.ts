import { api } from "./api";
import type { User } from "@/types";

export async function login(email: string, password: string): Promise<void> {
  const form = new URLSearchParams({ username: email, password });
  const { data } = await api.post<{ access_token: string }>("/api/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  localStorage.setItem("access_token", data.access_token);
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/api/auth/me");
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
  window.location.href = "/login";
}

export function getToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
}
