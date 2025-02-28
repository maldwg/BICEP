export function getAcceptedFileTypesForConfigurationType(fileType: string){
      switch (fileType) {
        case fileTypes.testData:
          return '.pcap,.csv,.pcap_ISX';
        case fileTypes.configuration:
          return '.yaml,.conf,.json,.lua';
        case fileTypes.ruleSet:
          return '.rules';
        default:
          return '*/*';
      }
}
    

export const fileTypes = {
    configuration: "configuration",
    ruleSet: "rule-set",
    testData: "test-data"
}