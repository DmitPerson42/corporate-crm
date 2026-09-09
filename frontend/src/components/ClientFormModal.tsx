import { useEffect, useState } from 'react';

import { App as AntdApp, Form, Input, Modal, Typography } from 'antd';

import { apiErrorText, fieldErrors } from '../api/http';
import type { ClientPayload, ClientRecord } from '../api/types';

interface Props {
  open: boolean;
  /** Передан — режим редактирования, null/undefined — создание. */
  client?: ClientRecord | null;
  onCancel: () => void;
  onSubmit: (values: ClientPayload) => Promise<void>;
}

const PHONE_PATTERN = /^\+?[\d][\d\s()\-]{4,19}$/;

export default function ClientFormModal({ open, client, onCancel, onSubmit }: Props) {
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<ClientPayload>();
  const [saving, setSaving] = useState(false);
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const isEdit = Boolean(client);

  useEffect(() => {
    if (!open) return;
    setServerErrors({});
    form.resetFields();
    form.setFieldsValue({
      last_name: client?.last_name ?? '',
      first_name: client?.first_name ?? '',
      middle_name: client?.middle_name ?? '',
      phone: client?.phone ?? '',
      email: client?.email ?? '',
      property_info: client?.property_info ?? '',
      comment: client?.comment ?? '',
    });
  }, [open, client, form]);

  const handleOk = async () => {
    let values: ClientPayload;
    try {
      values = await form.validateFields();
    } catch {
      return; // ошибки подсветит форма
    }
    setSaving(true);
    setServerErrors({});
    try {
      await onSubmit(values);
      message.success(isEdit ? 'Карточка клиента обновлена' : 'Клиент заведён в систему');
    } catch (error) {
      setServerErrors(fieldErrors(error));
      message.error(apiErrorText(error));
      return;
    } finally {
      setSaving(false);
    }
    onCancel();
  };

  const errorOf = (name: keyof ClientPayload) =>
    serverErrors[name] ? { validateStatus: 'error' as const, help: serverErrors[name] } : {};

  return (
    <Modal
      open={open}
      title={isEdit ? `Редактирование: ${client?.full_name}` : 'Новый клиент'}
      okText="Сохранить"
      cancelText="Отмена"
      confirmLoading={saving}
      onOk={handleOk}
      onCancel={onCancel}
      width={640}
      forceRender
    >
      <Form<ClientPayload> form={form} layout="vertical" requiredMark={false} autoComplete="off">
        <Form.Item
          name="last_name"
          label="Фамилия"
          rules={[
            { required: true, message: 'Фамилия обязательна' },
            { min: 2, message: 'Минимальная длина — 2 символа' },
          ]}
          {...errorOf('last_name')}
        >
          <Input placeholder="Петров" />
        </Form.Item>
        <div style={{ display: 'flex', gap: 12 }}>
          <Form.Item
            name="first_name"
            label="Имя"
            style={{ flex: 1 }}
            rules={[
              { required: true, message: 'Имя обязательно' },
              { min: 2, message: 'Минимальная длина — 2 символа' },
            ]}
            {...errorOf('first_name')}
          >
            <Input placeholder="Сергей" />
          </Form.Item>
          <Form.Item name="middle_name" label="Отчество" style={{ flex: 1 }} {...errorOf('middle_name')}>
            <Input placeholder="Алексеевич" />
          </Form.Item>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <Form.Item
            name="phone"
            label="Телефон"
            style={{ flex: 1 }}
            rules={[{ pattern: PHONE_PATTERN, message: 'Только цифры, +, скобки, дефис и пробел' }]}
            {...errorOf('phone')}
          >
            <Input placeholder="+7 (912) 345-67-89" />
          </Form.Item>
          <Form.Item
            name="email"
            label="E-mail"
            style={{ flex: 1 }}
            rules={[{ type: 'email', message: 'Некорректный адрес' }]}
            {...errorOf('email')}
          >
            <Input placeholder="petrov@example.ru" />
          </Form.Item>
        </div>
        <Form.Item
          name="property_info"
          label="Сведения об имуществе"
          {...errorOf('property_info')}
        >
          <Input.TextArea
            rows={3}
            maxLength={8000}
            showCount
            placeholder="Квартира 68 м², земельный участок 12 соток, автомобиль Skoda Octavia 2021 г."
          />
        </Form.Item>
        <Form.Item name="comment" label="Комментарий" {...errorOf('comment')}>
          <Input.TextArea
            rows={2}
            maxLength={8000}
            showCount
            placeholder="Например: ключевой клиент, договор №104 от 12.02.2025"
          />
        </Form.Item>
        {isEdit && (
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 13 }}>
            Дополнять карточку историей сообщений можно на её странице — поле «Комментарий» хранит
            первичную заметку.
          </Typography.Paragraph>
        )}
      </Form>
    </Modal>
  );
}
