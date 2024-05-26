export interface Container{
    id: number,
    name: string,
    host: string,
    port: number,
    status: string,
    description: string,
    configuration_id: number,
    ids_tool_id: number,
    ruleset_id?: number

}

export interface ContainerSetupData{
    host: string,
    ids_tool_id: number,
    configuration_id: number,
    description: string,
    ruleset_id?: number
}