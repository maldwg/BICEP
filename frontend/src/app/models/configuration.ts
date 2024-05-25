export interface Configuration{
    id: number,
    name: string,
    configuration: string,
    // neds to be with underscore otherwise backend error
    file_type: string,
    description: string
}

export interface ConfigurationSetupData{
    name: string,
    configuration: any,
    description: string,
    fileType: string
}


export const fileTpyes = {
    configuration: "configuration",
    ruleSet: "rule-set",
    testData: "test-data"
}