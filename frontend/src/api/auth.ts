import { http, tokenStore } from './http';
import type { Manager, TokenResponse } from './types';

/** Вход по логину и паролю: запоминаем токен и возвращаем данные менеджера. */
export async function login(login: string, password: string): Promise<Manager> {
  const { data } = await http.post<TokenResponse>('/api/auth/login', { login, password });
  tokenStore.set(data.access_token, data.expires_in);
  return data.manager;
}

export async function fetchMe(): Promise<Manager> {
  const { data } = await http.get<Manager>('/api/auth/me');
  return data;
}

export function logout(): void {
  tokenStore.clear();
}
