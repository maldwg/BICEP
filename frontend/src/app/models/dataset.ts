export interface Dataset{
    id: number,
    name: string,
    pcap_file: string,
    labels_file: string,
    description: string,
    ammount_benign: number,
    ammount_malicious: number
}

export interface DatasetSetupData{
    name: string,
    configuration: any,
    description: string,
}

export interface SerializedDataset {
    id: number,
    name: string,
    pcap_file: string, // Base64 encoded string
    labels_file: string, // Base64 encoded string
    description: string,
    ammount_benign: number,
    ammount_malicious: number
  }