export interface Manager {
  id: number;
  login: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  manager: Manager;
}

export interface ClientRecord {
  id: number;
  last_name: string;
  first_name: string;
  middle_name: string | null;
  phone: string | null;
  email: string | null;
  property_info: string | null;
  comment: string | null;
  full_name: string;
  comments_count: number;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientDetail extends ClientRecord {
  comments: CommentRecord[];
}

export interface CommentRecord {
  id: number;
  text: string;
  author_name: string;
  created_at: string;
}

export interface ClientListResponse {
  items: ClientRecord[];
  total: number;
  limit: number;
  offset: number;
}

/** Поля карточки, которые менеджер вводит в форме. */
export interface ClientPayload {
  last_name: string;
  first_name: string;
  middle_name?: string | null;
  phone?: string | null;
  email?: string | null;
  property_info?: string | null;
  comment?: string | null;
}
