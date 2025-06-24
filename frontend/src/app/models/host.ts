export interface DockerHostSystem{
    id: number,
    name: string,
    host: string,
    docker_port: number,
    status?: string
}

export interface DockerHostSystemCreationData {
    name: string,
    host: string,
    docker_port?: number
}