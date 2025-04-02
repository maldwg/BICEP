"""
The following method shows, how to implement a method for an ensembling technique
    1. Add a database entry for your new algorithm
    2. create a new python file in this directory here, named exactly as the function_name property you selcted for the database entry
    3. implement an async method called the same as the function_name property you selected
"""
from app.bicep_utils.models.ids_base import Alert
from app.logger import LOGGER

async def sample(alerts_dict: dict, ensemble) -> list[Alert]:
    """
    Method to calculate which alerts of an ensemble are majority voted ones

    Args:
        alerts_dict (dict): Dict that holds for each IDS in the ensemble a list of alerts
        ensemble: (Ensemble): Ensemble Object according to the ORM

    Returns:
        voted_alerts (list[Alert]): List of alerts the ensemble voted for using a specific algorithm
    """
    pass
