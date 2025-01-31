import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface UserCreate {
  email: string;
  password: string;
}

export interface User {
  email: string;
  id: number;
  is_active: boolean;
  settings?: UserSettings;
}

export interface UserSettings {
  export_location?: string;
  export_type?: string;
  max_parallel_queries?: number;
  ssh_hostname?: string;
  ssh_port?: number;
  ssh_username?: string;
}

export interface Query {
  query_text: string;
  db_username: string;
  db_password: string;
  db_tns: string;
  export_location?: string;
  export_type?: string;
  export_filename?: string;
  ssh_hostname?: string;
  id: number;
  user_id: number;
  status: 'pending' | 'queued' | 'running' | 'transferring' | 'completed' | 'failed';
  error_message?: string;
  result_metadata?: any;
  created_at: string;
  started_at?: string;
  updated_at?: string;
  completed_at?: string;
}

const auth = {
  login: (credentials: LoginCredentials) => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
  register: (userData: UserCreate) => api.post('/auth/register', userData),
};

const users = {
  getProfile: () => api.get('/users/profile'),
  getSettings: () => api.get('/users/settings'),
  updateSettings: (settings: UserSettings) => api.put('/users/settings', settings),
};

const queries = {
  list: () => api.get('/queries/query'),
  create: (query: Omit<Query, 'id' | 'user_id' | 'status' | 'created_at'>) => 
    api.post('/queries/query', query),
  getStatus: (queryId: number) => api.get(`/queries/${queryId}`),
  delete: (queryId: number) => api.delete(`/queries/${queryId}`),
  rerun: (queryId: number) => api.post(`/queries/${queryId}/rerun`),
  batchRerun: (queryIds: number[]) => api.post('/queries/batch/rerun', { query_ids: queryIds }),
  batchDelete: (queryIds: number[]) => api.post('/queries/batch/delete', { query_ids: queryIds }),
  getCurrentStats: () => api.get('/queries/stats/current'),
};

export const apiClient = {
  auth,
  users,
  queries,
}; 