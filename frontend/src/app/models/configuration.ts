export interface Configuration{
    id: number,
    configuration: string,
    description: string
}

export interface ConfigurationSetupData{
    name: string,
    configuration: File,
    description: string
}