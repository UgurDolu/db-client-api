export interface User {
    id: number;
    email: string;
    is_active: boolean;
    settings?: UserSettings;
}

export interface UserSettings {
    export_type: string;
    export_location: string;
    max_parallel_queries: number;
    ssh_username: string;
    ssh_password: string;
    ssh_key: string;
    ssh_key_passphrase: string;
}

export interface SSHSettings {
    ssh_username: string;
    ssh_password: string;
    ssh_key: string;
    ssh_key_passphrase: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface Query {
    id: number;
    user_id: number;
    db_username: string;
    db_tns: string;
    query_text: string;
    status: QueryStatus;
    export_location?: string;
    export_type?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    error_message?: string;
    result_metadata?: any;
}

export enum QueryStatus {
    PENDING = "pending",
    QUEUED = "queued",
    RUNNING = "running",
    COMPLETED = "completed",
    FAILED = "failed"
}

export interface QueryResult {
    data: any[];
    metadata: {
        total_rows: number;
        execution_time: number;
        export_path?: string;
    };
}

export interface APIError {
    detail: string;
    status_code: number;
} 