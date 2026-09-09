import axios, { AxiosError } from 'axios';

import { fieldLabel } from './fields';

const TOKEN_KEY = 'crm.access_token';
const EXPIRES_KEY = 'crm.access_token_expires_at';

/** Хранилище токена. В реальном проекте лучше httpOnly-cookie, для учебного — localStorage. */
export const tokenStore = {
  get(): string | null {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;
    const expiresAt = Number(localStorage.getItem(EXPIRES_KEY) ?? 0);
    if (expiresAt && expiresAt <= Date.now()) {
      tokenStore.clear();
      return null;
    }
    return token;
  },
  set(token: string, lifetimeSeconds: number): void {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(EXPIRES_KEY, String(Date.now() + lifetimeSeconds * 1000));
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EXPIRES_KEY);
  },
};

// Вызывается из AuthContext, когда сервер отверг токен: сбрасываем сессию и уходим на вход.
let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export const http = axios.create({
  // Пустой baseURL => запросы идут на тот же источник и попадают на прокси Vite (см. vite.config.ts).
  baseURL: import.meta.env.VITE_API_URL ?? '',
  timeout: 15000,
});

http.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    const url = error.config?.url ?? '';
    // Просроченный или подделанный токен: выходим из системы, но сам запрос на вход не трогаем.
    if (status === 401 && !url.includes('/api/auth/login')) {
      tokenStore.clear();
      unauthorizedHandler?.();
    }
    return Promise.reject(error);
  },
);

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

function issueField(issue: ValidationIssue): string {
  const loc = issue.loc ?? [];
  const last = loc.filter((part) => part !== 'body').pop();
  return typeof last === 'string' ? last : '';
}

function issueText(issue: ValidationIssue): string {
  const message = (issue.msg ?? 'некорректное значение').replace(/^Value error,\s*/i, '');
  const field = issueField(issue);
  return field ? `${fieldLabel(field)}: ${message}` : message;
}

/** Человеческое описание ошибки ответа API для message.error(...). */
export function apiErrorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: string | ValidationIssue[] } | undefined;
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail;
      const texts = Array.from(new Set(data.detail.map(issueText)));
      return texts.join('; ');
    }
    if (!error.response) {
      return 'Сервер недоступен. Проверьте, что backend запущен на http://127.0.0.1:8000, а PostgreSQL — на 127.0.0.1:5432.';
    }
    return `Ошибка ${error.response.status}. Обновите страницу и повторите действие.`;
  }
  return error instanceof Error ? error.message : 'Неизвестная ошибка';
}

/** Ошибки валидации по полям формы — antd подсветит конкретные инпуты. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error)) return {};
  const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
  if (!Array.isArray(detail)) return {};
  const result: Record<string, string> = {};
  for (const issue of detail as ValidationIssue[]) {
    const field = issueField(issue);
    if (field && !result[field]) result[field] = (issue.msg ?? '').replace(/^Value error,\s*/i, '');
  }
  return result;
}
