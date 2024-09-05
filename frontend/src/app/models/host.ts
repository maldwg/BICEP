export interface HostSystem{
    id: number,
    name: string,
    host: string,
    docker_port: number
}

export interface HostSystemCreationData {
    name: string,
    host: string,
    docker_port?: number
}