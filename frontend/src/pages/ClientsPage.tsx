import { useEffect, useState } from 'react';

import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Input,
  Popconfirm,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

import { createClient, deleteClient, listClients } from '../api/clients';
import ClientFormModal from '../components/ClientFormModal';
import { apiErrorText } from '../api/http';
import type { ClientPayload, ClientRecord } from '../api/types';

const formatDate = (value: string) => dayjs(value).format('DD.MM.YYYY HH:mm');

export default function ClientsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = AntdApp.useApp();

  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [createOpen, setCreateOpen] = useState(false);

  // Поиск отправляем на сервер с задержкой: не дёргаем БД на каждом нажатии клавиши.
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isFetching, isError, error, refetch } = useQuery({
    queryKey: ['clients', { query, page, pageSize }],
    queryFn: () =>
      listClients({ q: query || undefined, limit: pageSize, offset: (page - 1) * pageSize }),
    placeholderData: keepPreviousData,
  });

  const createMutation = useMutation({
    mutationFn: (payload: ClientPayload) => createClient(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      setCreateOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteClient(id),
    onSuccess: (_result, id) => {
      message.success(`Клиент №${id} удалён`);
      queryClient.invalidateQueries({ queryKey: ['clients'] });
    },
    onError: (err) => message.error(apiErrorText(err)),
  });

  const columns = [
    {
      title: 'ФИО',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (_: string, record: ClientRecord) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{record.full_name}</Typography.Text>
          {record.created_by_name && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              завёл: {record.created_by_name}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
      width: 180,
      render: (value: string | null) => value ?? <Typography.Text type="secondary">—</Typography.Text>,
    },
    {
      title: 'E-mail',
      dataIndex: 'email',
      key: 'email',
      width: 220,
      render: (value: string | null) => value ?? <Typography.Text type="secondary">—</Typography.Text>,
    },
    {
      title: 'Сведения об имуществе',
      dataIndex: 'property_info',
      key: 'property_info',
      ellipsis: { showTitle: false },
      render: (value: string | null) =>
        value ? (
          <Tooltip title={value} placement="topLeft">
            <span className="property-cell">{value}</span>
          </Tooltip>
        ) : (
          <Typography.Text type="secondary">—</Typography.Text>
        ),
    },
    {
      title: 'Комментариев',
      dataIndex: 'comments_count',
      key: 'comments_count',
      width: 130,
      render: (value: number) => (value ? <Tag color="blue">{value}</Tag> : '—'),
    },
    {
      title: 'Обновлено',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (value: string) => formatDate(value),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: ClientRecord) => (
        <Space onClick={(event) => event.stopPropagation()}>
          <Button size="small" type="link" onClick={() => navigate(`/clients/${record.id}`)}>
            Открыть
          </Button>
          <Popconfirm
            title="Удалить клиента?"
            description="Карточка и её комментарии будут удалены безвозвратно."
            okText="Удалить"
            okButtonProps={{ danger: true }}
            cancelText="Отмена"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button size="small" type="link" danger>
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Typography.Title level={3} className="page-title">
        Клиенты
      </Typography.Title>
      <Typography.Paragraph type="secondary" className="page-subtitle">
        Единый реестр клиентов компании: карточки, реквизиты и история дополнений.
      </Typography.Paragraph>

      <Card>
        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} wrap>
          <Input
            allowClear
            placeholder="Поиск по ФИО, телефону, e-mail, имуществу"
            style={{ width: 380 }}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            prefix={<SearchOutlined style={{ color: 'rgba(0,0,0,0.25)' }} />}
          />
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isFetching}>
              Обновить
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              Новый клиент
            </Button>
          </Space>
        </Space>

        {isError && (
          <Alert
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            message="Не удалось загрузить список клиентов"
            description={apiErrorText(error)}
            action={
              <Button size="small" onClick={() => refetch()}>
                Повторить
              </Button>
            }
          />
        )}

        <Table<ClientRecord>
          rowKey="id"
          columns={columns}
          dataSource={data?.items ?? []}
          loading={isFetching && !data}
          locale={{
            emptyText: query
              ? `По запросу «${query}» ничего не найдено`
              : 'Клиентов пока нет — заведите первого',
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/clients/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current: page,
            pageSize,
            total: data?.total ?? 0,
            showSizeChanger: true,
            pageSizeOptions: [10, 25, 50, 100],
            showTotal: (total) => `Всего карточек: ${total}`,
            onChange: (nextPage, nextSize) => {
              setPage(nextPage);
              setPageSize(nextSize);
            },
          }}
        />
      </Card>

      <ClientFormModal
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onSubmit={async (values) => {
          await createMutation.mutateAsync(values);
        }}
      />
    </>
  );
}
