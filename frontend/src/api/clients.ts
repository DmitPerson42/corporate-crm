import { http } from './http';
import type {
  ClientDetail,
  ClientListResponse,
  ClientPayload,
  ClientRecord,
  CommentRecord,
} from './types';

export interface ClientListQuery {
  q?: string;
  limit: number;
  offset: number;
}

export async function listClients(query: ClientListQuery): Promise<ClientListResponse> {
  const { data } = await http.get<ClientListResponse>('/api/clients', { params: query });
  return data;
}

export async function getClient(id: number): Promise<ClientDetail> {
  const { data } = await http.get<ClientDetail>(`/api/clients/${id}`);
  return data;
}

export async function createClient(payload: ClientPayload): Promise<ClientRecord> {
  const { data } = await http.post<ClientRecord>('/api/clients', payload);
  return data;
}

export async function updateClient(
  id: number,
  payload: Partial<ClientPayload>,
): Promise<ClientRecord> {
  const { data } = await http.put<ClientRecord>(`/api/clients/${id}`, payload);
  return data;
}

export async function deleteClient(id: number): Promise<void> {
  await http.delete(`/api/clients/${id}`);
}

export async function addComment(clientId: number, text: string): Promise<CommentRecord> {
  const { data } = await http.post<CommentRecord>(`/api/clients/${clientId}/comments`, { text });
  return data;
}
