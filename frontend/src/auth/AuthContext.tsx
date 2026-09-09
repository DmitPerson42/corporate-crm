import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { fetchMe, login as requestLogin, logout as clearToken } from '../api/auth';
import { setUnauthorizedHandler, tokenStore } from '../api/http';
import type { Manager } from '../api/types';

interface AuthContextValue {
  manager: Manager | null;
  /** true, пока проверяем сохранённый токен при первой загрузке страницы. */
  initializing: boolean;
  signIn: (login: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [manager, setManager] = useState<Manager | null>(null);
  const [initializing, setInitializing] = useState(true);

  // Если токен истёк или его подделали, backend отвечает 401 — роняем сессию в интерфейс.
  useEffect(() => {
    setUnauthorizedHandler(() => setManager(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!tokenStore.get()) {
        setInitializing(false);
        return;
      }
      try {
        const current = await fetchMe();
        if (!cancelled) setManager(current);
      } catch {
        clearToken();
      } finally {
        if (!cancelled) setInitializing(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (login: string, password: string) => {
    const current = await requestLogin(login, password);
    setManager(current);
  }, []);

  const signOut = useCallback(() => {
    clearToken();
    setManager(null);
  }, []);

  const value = useMemo(
    () => ({ manager, initializing, signIn, signOut }),
    [manager, initializing, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth должен вызываться внутри <AuthProvider>');
  return context;
}
