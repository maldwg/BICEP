export interface Container{
    id: number,
    url: string,
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