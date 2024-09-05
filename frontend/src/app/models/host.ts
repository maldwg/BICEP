export interface DockerHostSystem{
    id: number,
    name: string,
    host: string,
    docker_port: number
}

export interface DockerHostSystemCreationData {
    name: string,
    host: string,
    docker_port?: number
}