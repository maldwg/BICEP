"""
The purpose of this smaple file is to give developers a directive howto implement their own ensembling algorithms
1. Add a database entry for your new algorithm
2. create a new python file in this directory here, named exactly as the function_name property you selcted for the database entry
3. implement an async method called the same as the function_name property you selected
"""
from ...bicep_utils.models.ids_base import Alert
from ...logger import LOGGER

async def sample(alerts_dict: dict, ensemble) -> list[Alert]:
    """
        The method takes as input the common alerts of an ensemble, as well as the ensemble instance.
        The format of the alerts_dict alerts is as follows:
            {
                ids1: list[Alert],
                ids2: list[Alert],
                ....
            }

        You might need to convert this dict into another form, so that you are able to know which alerts are commonly outputted by the IDS and which are not.
        as an example, the majority vote convertss the alerts_dict to such a structure:

            {
                ts-src_ip-src_port-dst_ip-dst_port: {
                    "ids1": list[Alert],
                    "ids2": list[Alert]
                }, 
                ts2-src_ip2-src_port2-dst_ip2-dst_port2: {
                    "ids1": list[Alert],
                    "ids2": list[Alert]
                }, 
            }
        This allows to directly know which alert has been issiued by which IDS, as the keys of the dict are quasi unique.
        return: Should return a list of Alerts that the ensemble consdiers as agreed upon by the individual IDS
    """
    # return majority_voted_alerts
    pass
