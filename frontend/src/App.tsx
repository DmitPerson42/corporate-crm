import { Spin } from 'antd';
import type { ReactElement } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import AppLayout from './components/AppLayout';
import ClientPage from './pages/ClientPage';
import ClientsPage from './pages/ClientsPage';
import LoginPage from './pages/LoginPage';
import { useAuth } from './auth/AuthContext';

function RequireAuth({ children }: { children: ReactElement }) {
  const { manager, initializing } = useAuth();

  if (initializing) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large">
          <div style={{ padding: 40 }} />
        </Spin>
      </div>
    );
  }

  if (!manager) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { manager } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={manager ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<ClientsPage />} />
        <Route path="/clients/:id" element={<ClientPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
