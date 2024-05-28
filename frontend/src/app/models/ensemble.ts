export interface Ensemble {

    id: number,
    name: string,
    technique_id: number,
    description: string,
    status: string

}


export interface EnsembleTechnqiue{
    id: number,
    name: string,
    description: string
}

export interface EnsembleSetupData{
    name: string,
    description: string,
    technique: number,
    // Important to let this with underscore to be able to communicate with the backend
    container_ids: number[],
}



export interface EnsembleUpdateData{
    id: number,
    name: string,
    description: string,
    technique_id: number,
    container_ids: number[],
}

export interface EnsembleContainer{
    id: number,
    ensemble_id: number,
    ids_container_id: number
}