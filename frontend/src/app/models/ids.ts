export interface IdsTool {
    id: number,
    name: string,
    ids_type: string,
    analysis_method: string,
    requires_ruleset: boolean,
    image_name: string,
    image_tag: string,
    deployment_type: string,
    required_env_vars: string  // comma-separated list of mandatory env var names
}

export interface IdsToolCreateData {
    name: string,
    ids_type: string,
    analysis_method: string,
    requires_ruleset: boolean,
    image_name: string,
    image_tag: string,
    deployment_type: string,
    required_env_vars: string
}

export interface IdsToolUpdateData {
    id: number,
    name: string,
    ids_type: string,
    analysis_method: string,
    requires_ruleset: boolean,
    image_name: string,
    image_tag: string,
    deployment_type: string,
    required_env_vars: string
}
