export interface Ensemble {

    id: number,
    name: string,
    techniqueId: number,
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