export interface Dataset{
    id: number,
    name: string,
    data_file_path: string,
    labels_file_path: string,
    description: string,
    ammount_benign: number,
    ammount_malicious: number,
    dataset_type_id: number,
}

export interface DatasetSetupData{
    name: string,
    data_file: any,
    labels_file: any,
    description: string,
    dataset_type_id: string
}