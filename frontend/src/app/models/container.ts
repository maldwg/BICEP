export interface Container{
    id: number,
    name: string,
    host: string,
    port: number,
    status: string,
    description: string,
    configuration_id: number,
    ids_tool_id: number,
    ruleset_id?: number,
    // TODO: adjust frontend to also display if currently metrics are sended
    stream_metric_task_id?: string

}

export interface ContainerSetupData{
    host: string,
    ids_tool_id: number,
    configuration_id: number,
    description: string,
    ruleset_id?: number
}


export interface ContainerUpdateData{
    id: number,
    configuration_id: number,
    description: string,
    ruleset_id?: number
}