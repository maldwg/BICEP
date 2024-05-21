export interface Container{
    id: number,
    name: string,
    host: string,
    port: number,
    status: string,
    description: string,
    configurationId: number,
    idsTooId: number
}

export interface ContainerSetupData{
    host: string,
    idsToolId: number,
    configurationId: number,
    description: string,
}