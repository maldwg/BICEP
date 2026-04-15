export interface RegisteredMetricService {
    id: number,
    host_system_id: number,
    name: string,
    ip?: string,
    port?: number,
    status: string,
    status_message?: string,
    last_registration_at?: string
}

export interface DockerHostSystem{
    id: number,
    name: string,
    host: string,
    docker_port: number,
    status?: string,
    status_message?: string,
    metric_service?: RegisteredMetricService | null
}

export interface DockerHostSystemCreationData {
    name: string,
    host: string,
    docker_port?: number
}
