export interface Configuration {
  id: number,
  name: string,
  file_path: string,
  file_type: string,
  description: string,
  config_type?: string
}

export interface ConfigurationSetupData {
  name: string,
  configuration: any,
  description: string,
  file_type: string
}

export interface DeserializedConfiguration {
  id: number;
  name: string;
  file_type: string;
  file_content: string;
  file_path: string;
  description: string;
}


export interface SerializedConfiguration {
  id: number;
  name: string;
  file_type: string;
  file_content: string;
  file_path: string;
  description: string;
}

