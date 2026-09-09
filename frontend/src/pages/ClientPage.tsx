import { useState } from 'react';

import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  Popconfirm,
  Result,
  Skeleton,
  Space,
  Timeline,
  Typography,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import { useNavigate, useParams } from 'react-router-dom';

import { addComment, deleteClient, getClient, updateClient } from '../api/clients';
import ClientFormModal from '../components/ClientFormModal';
import { apiErrorText } from '../api/http';
import type { ClientPayload } from '../api/types';

const formatDate = (value: string) => dayjs(value).format('DD.MM.YYYY HH:mm');
const dash = <Typography.Text type="secondary">не указано</Typography.Text>;

export default function ClientPage() {
  const { id } = useParams();
  const clientId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = AntdApp.useApp();
  const [editOpen, setEditOpen] = useState(false);
  const [commentText, setCommentText] = useState('');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => getClient(clientId),
    enabled: Number.isInteger(clientId) && clientId > 0,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['client', clientId] });
    queryClient.invalidateQueries({ queryKey: ['clients'] });
  };

  const updateMutation = useMutation({
    mutationFn: (payload: ClientPayload) => updateClient(clientId, payload),
    onSuccess: refresh,
  });

  const commentMutation = useMutation({
    mutationFn: (text: string) => addComment(clientId, text),
    onSuccess: () => {
      setCommentText('');
      message.success('Карточка дополнена');
      refresh();
    },
    onError: (err) => message.error(apiErrorText(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteClient(clientId),
    onSuccess: () => {
      message.success('Клиент удалён');
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      navigate('/', { replace: true });
    },
    onError: (err) => message.error(apiErrorText(err)),
  });

  if (isError) {
    const notFound = axios.isAxiosError(error) && error.response?.status === 404;
    if (notFound) {
      return (
        <Result
          status="404"
          title="Клиент не найден"
          subTitle="Возможно, карточку удалили или ссылка устарела."
          extra={
            <Button type="primary" onClick={() => navigate('/')}>
              К списку клиентов
            </Button>
          }
        />
      );
    }
    return (
      <Alert
        type="error"
        showIcon
        message="Не удалось загрузить карточку"
        description={apiErrorText(error)}
        action={
          <Button size="small" onClick={() => queryClient.invalidateQueries({ queryKey: ['client', clientId] })}>
            Повторить
          </Button>
        }
      />
    );
  }

  if (isLoading || !data) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    );
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          К списку
        </Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {data.full_name}
        </Typography.Title>
        <Typography.Text type="secondary">карточка №{data.id}</Typography.Text>
      </Space>

      <Card
        title="Карточка клиента"
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Button icon={<EditOutlined />} type="primary" onClick={() => setEditOpen(true)}>
              Редактировать
            </Button>
            <Popconfirm
              title="Удалить клиента?"
              description="Карточка и её комментарии будут удалены безвозвратно."
              okText="Удалить"
              okButtonProps={{ danger: true }}
              cancelText="Отмена"
              onConfirm={() => deleteMutation.mutate()}
            >
              <Button icon={<DeleteOutlined />} danger loading={deleteMutation.isPending}>
                Удалить
              </Button>
            </Popconfirm>
          </Space>
        }
      >
        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="middle">
          <Descriptions.Item label="Фамилия">{data.last_name}</Descriptions.Item>
          <Descriptions.Item label="Имя">{data.first_name}</Descriptions.Item>
          <Descriptions.Item label="Отчество">{data.middle_name ?? dash}</Descriptions.Item>
          <Descriptions.Item label="Телефон">{data.phone ?? dash}</Descriptions.Item>
          <Descriptions.Item label="E-mail" span={2}>
            {data.email ?? dash}
          </Descriptions.Item>
          <Descriptions.Item label="Сведения об имуществе" span={2}>
            {data.property_info ? (
              <Typography.Paragraph className="comment-text" style={{ marginBottom: 0 }}>
                {data.property_info}
              </Typography.Paragraph>
            ) : (
              dash
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Комментарий" span={2}>
            {data.comment ? (
              <Typography.Paragraph className="comment-text" style={{ marginBottom: 0 }}>
                {data.comment}
              </Typography.Paragraph>
            ) : (
              dash
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Завёл">
            {data.created_by_name ?? 'сведения недоступны'}
          </Descriptions.Item>
          <Descriptions.Item label="Создана">{formatDate(data.created_at)}</Descriptions.Item>
          <Descriptions.Item label="Обновлена">{formatDate(data.updated_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={`История дополнений (${data.comments.length})`}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Input.TextArea
            rows={3}
            maxLength={4000}
            showCount
            placeholder="Новое дополнение к карточке: итоги переговоров, изменения по имуществу, поручения…"
            value={commentText}
            onChange={(event) => setCommentText(event.target.value)}
            disabled={commentMutation.isPending}
          />
          <Space>
            <Button
              type="primary"
              loading={commentMutation.isPending}
              disabled={!commentText.trim()}
              onClick={() => commentMutation.mutate(commentText.trim())}
            >
              Дополнить карточку
            </Button>
            {commentText && (
              <Button onClick={() => setCommentText('')} disabled={commentMutation.isPending}>
                Очистить
              </Button>
            )}
          </Space>

          {data.comments.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Комментариев пока нет — карточку можно дополнить выше"
            />
          ) : (
            <Timeline
              items={data.comments.map((comment) => ({
                key: comment.id,
                color: 'blue',
                children: (
                  <Space direction="vertical" size={2}>
                    <Typography.Text className="comment-text">{comment.text}</Typography.Text>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {comment.author_name} · {formatDate(comment.created_at)}
                    </Typography.Text>
                  </Space>
                ),
              }))}
            />
          )}
        </Space>
      </Card>

      <ClientFormModal
        open={editOpen}
        client={data}
        onCancel={() => setEditOpen(false)}
        onSubmit={async (values) => {
          await updateMutation.mutateAsync(values);
        }}
      />
    </>
  );
}
