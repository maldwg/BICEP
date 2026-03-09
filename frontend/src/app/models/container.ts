export interface IdsSystem {
    id: number,
    name: string,
    host_system_id: number,
    port: number,
    status: string,
    description: string,
    configuration_id: number,
    ids_tool_id: number,
    ruleset_id?: number,
    runtime_configuration_id?: number,
    stream_metric_task_id?: string,
    type: string  // NIDS, HIDS, CIDS
}

// Alias for backward compatibility - prefer using IdsSystem in new code
export type Container = IdsSystem;

export interface ContainerSetupData {
    host_system_id: number,
    ids_tool_id: number,
    configuration_id: number,
    description: string,
    ruleset_id?: number,
    cids_configurations?: CidsServiceConfig[],
    runtime_configuration_id?: number,
    type?: string,  // NIDS, HIDS, CIDS - defaults to NIDS
    env_vars?: { [key: string]: string }
}

export interface ComposeService {
    name: string,
    is_sensor: boolean
}

export interface CidsServiceConfig {
    service_name: string,
    host_system_id: number,
    count: number,
    is_sensor?: boolean
}


export interface ContainerUpdateData {
    id: number,
    configuration_id: number,
    description: string,
    ruleset_id?: number
}