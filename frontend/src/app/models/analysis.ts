export const analysisTypes = {
    static: "static",
    network: "network"
}

export interface StaticAnalysisData {
    dataset_id: number,
    container_id?: number,
    ensemble_id?: number
}

export interface NetworkAnalysisData {
    container_id?: number,
    ensemble_id?: number

}
export interface stop_analysisData{
    container_id?: number,
    ensemble_id?: number
}