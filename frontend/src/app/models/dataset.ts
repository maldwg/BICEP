export interface Dataset{
    id: number,
    name: string,
    pcap_file_path: string,
    labels_file_path: string,
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
    pcap_file_path: string,
    labels_file_path: string, 
    description: string,
    ammount_benign: number,
    ammount_malicious: number
  }