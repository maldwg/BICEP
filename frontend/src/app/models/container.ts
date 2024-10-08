export interface Container{
    id: number,
    name: string,
    host_system_id: number,
    port: number,
    status: string,
    description: string,
    configuration_id: number,
    ids_tool_id: number,
    ruleset_id?: number,
    stream_metric_task_id?: string

}

export interface ContainerSetupData{
    host_system_id: number,
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