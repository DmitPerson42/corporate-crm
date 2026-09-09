import { App as AntdApp, Layout, Menu, Typography } from 'antd';
import { Link, Outlet, useNavigate } from 'react-router-dom';

import { TeamOutlined, UserOutlined } from '@ant-design/icons';

import { useAuth } from '../auth/AuthContext';

const { Header, Content, Footer } = Layout;

export default function AppLayout() {
  const { manager, signOut } = useAuth();
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          paddingInline: 24,
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <Typography.Text strong style={{ color: '#fff', fontSize: 16, whiteSpace: 'nowrap' }}>
          КИС «Учёт клиентов»
        </Typography.Text>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={['clients']}
          style={{ flex: 1, minWidth: 200, borderBottom: 'none' }}
          items={[{ key: 'clients', icon: <TeamOutlined />, label: <Link to="/">Клиенты</Link> }]}
        />
        {manager && (
          <Typography.Text style={{ color: 'rgba(255,255,255,0.85)' }} ellipsis>
            <UserOutlined style={{ marginRight: 8 }} />
            {manager.full_name}
          </Typography.Text>
        )}
        <Typography.Link
          style={{ color: 'rgba(255,255,255,0.85)' }}
          onClick={() => {
            signOut();
            message.success('Сессия завершена');
            navigate('/login', { replace: true });
          }}
        >
          Выйти
        </Typography.Link>
      </Header>
      <Content style={{ padding: '24px 32px', maxWidth: 1400, width: '100%', margin: '0 auto' }}>
        <Outlet />
      </Content>
      <Footer style={{ textAlign: 'center', color: 'rgba(0,0,0,0.45)' }}>
        Учебный проект · корпоративная информационно-аналитическая система · PostgreSQL + FastAPI +
        React
      </Footer>
    </Layout>
  );
}
