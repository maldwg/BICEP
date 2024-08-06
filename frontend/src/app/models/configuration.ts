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
    file_type: string
}


export const fileTypes = {
    configuration: "configuration",
    ruleSet: "rule-set",
    testData: "test-data"
}


export interface SerializedConfiguration {
    id: number;
    name: string;
    configuration: string; // Base64 encoded string
    file_type: string;
    description: string;
  }