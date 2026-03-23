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
    type?: string,  // NIDS, HIDS, CIDS - defaults to NIDS
    env_vars?: { [key: string]: string }
}

export interface ComposeService {
    name: string,
    is_sensor: boolean,
    config_mount_path?: string | null,
    expected_config_extension?: string | null,
}

export interface CidsServiceConfig {
    service_name: string,
    host_system_id: number,
    count: number,
    runtime_configuration_id?: number | null,
    is_sensor?: boolean,
    config_mount_path?: string | null,
    expected_config_extension?: string | null,
}


export interface ContainerUpdateData {
    id: number,
    configuration_id: number,
    description: string,
    ruleset_id?: number
}
