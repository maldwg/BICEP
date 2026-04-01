export function getAcceptedFileTypesForConfigurationType(fileType: string){
      switch (fileType) {
        case fileTypes.dataset:
          return '.pcap,.csv,.pcap_ISX';
        case fileTypes.runtime:
          return '.yaml,.conf,.json,.lua';
        case fileTypes.deployment:
          return '.yaml,.yml';
        case fileTypes.ruleSet:
          return '.rules';
        default:
          return '*/*';
      }
}
    

export const fileTypes = {
    runtime: "RUNTIME",
    deployment: "DEPLOYMENT",
    ruleSet: "RULESET",
    dataset: "DATASET"
}