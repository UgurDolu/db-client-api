import axios from 'axios';
import {
    User,
    UserSettings,
    SSHSettings,
    LoginResponse,
    Query,
    QueryResult,
} from '../types/api';

const API_URL = 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Auth API
export const authApi = {
    login: async (email: string, password: string): Promise<LoginResponse> => {
        const formData = new FormData();
        formData.append('username', email);  // OAuth2 expects 'username'
        formData.append('password', password);
        const response = await api.post<LoginResponse>('/auth/login', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    register: async (email: string, password: string): Promise<User> => {
        const response = await api.post<User>('/auth/register', { email, password });
        return response.data;
    },
};

// User Settings API
export const userApi = {
    getSettings: async (): Promise<UserSettings> => {
        const response = await api.get<UserSettings>('/users/settings');
        return response.data;
    },

    updateSettings: async (settings: Partial<UserSettings>): Promise<UserSettings> => {
        const response = await api.put<UserSettings>('/users/settings', settings);
        return response.data;
    },

    updateSSHSettings: async (sshSettings: SSHSettings): Promise<UserSettings> => {
        const response = await api.put<UserSettings>('/users/settings/ssh', sshSettings);
        return response.data;
    },

    testSSHConnection: async (sshSettings: SSHSettings): Promise<{ message: string; files: string }> => {
        const response = await api.post<{ message: string; files: string }>('/users/settings/ssh/test', sshSettings);
        return response.data;
    },
};

// Queries API
export const queriesApi = {
    getQueries: async (): Promise<Query[]> => {
        const response = await api.get<Query[]>('/queries');
        return response.data;
    },

    createQuery: async (queryData: {
        db_username: string;
        db_password: string;
        db_tns: string;
        query_text: string;
        export_type?: string;
        export_location?: string;
    }): Promise<Query> => {
        const response = await api.post<Query>('/queries', queryData);
        return response.data;
    },

    getQueryStatus: async (queryId: string): Promise<Query> => {
        const response = await api.get<Query>(`/queries/${queryId}/status`);
        return response.data;
    },

    getQueryResults: async (queryId: string): Promise<QueryResult> => {
        const response = await api.get<QueryResult>(`/queries/${queryId}/results`);
        return response.data;
    },
};

export default {
    auth: authApi,
    user: userApi,
    queries: queriesApi,
}; 