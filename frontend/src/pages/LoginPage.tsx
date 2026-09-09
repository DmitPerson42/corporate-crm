import { useState } from 'react';

import { App as AntdApp, Button, Card, Form, Input, Typography } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';

import { apiErrorText, fieldErrors } from '../api/http';
import { useAuth } from '../auth/AuthContext';

interface FormValues {
  login: string;
  password: string;
}

export default function LoginPage() {
  const { signIn } = useAuth();
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true);
    setServerErrors({});
    try {
      await signIn(values.login, values.password);
      message.success('Вход выполнен');
    } catch (error) {
      setServerErrors(fieldErrors(error));
      message.error(apiErrorText(error));
      form.setFieldsValue({ password: '' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1677ff 0%, #0b2545 100%)',
        padding: 16,
      }}
    >
      <Card style={{ width: 400, boxShadow: '0 12px 32px rgba(0,0,0,0.24)' }}>
        <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
          Учёт клиентов
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          Корпоративная информационно-аналитическая система. Доступ — для менеджеров.
        </Typography.Paragraph>

        <Form<FormValues>
          form={form}
          layout="vertical"
          onFinish={onSubmit}
          requiredMark={false}
          autoComplete="off"
          initialValues={{ login: 'manager' }}
        >
          <Form.Item
            name="login"
            label="Логин"
            validateStatus={serverErrors.login ? 'error' : undefined}
            help={serverErrors.login}
            rules={[{ required: true, message: 'Введите логин' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="manager" size="large" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            validateStatus={serverErrors.password ? 'error' : undefined}
            help={serverErrors.password}
            rules={[{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="••••••••" size="large" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block size="large" loading={submitting}>
              Войти
            </Button>
          </Form.Item>
        </Form>

        <Typography.Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 13 }}>
          Учётная запись из начального наполнения базы:{' '}
          <Typography.Text code>manager / manager123</Typography.Text>
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
