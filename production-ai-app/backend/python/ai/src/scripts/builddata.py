import os
import sys

# Sets Location to access local functions
module_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "helpers/builddata")
)
sys.path.append(module_path)

from helpers.builddata.clients import getAllClients
from helpers.builddata.wants import getWants
from helpers.builddata.sector import getSectors
from helpers.builddata.sectWants import getSectorWants


# Runs all of the needed scripts to create data
def buildData(projectName: str = "Default"):

    getAllClients(projectName)
    getWants(projectName)
    getSectors(projectName)
    getSectorWants(projectName)


buildData("Salinity")
