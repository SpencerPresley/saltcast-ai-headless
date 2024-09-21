import os
import sys

# Sets Location to access local functions
module_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "helpers/loaddocs")
)
sys.path.append(module_path)

from helpers.loaddocs import convertFiles
from helpers.loaddocs import loadFiles


def loadDocs(projectName: str = "Default"):
    convertFiles(projectName)
    loadFiles(projectName)


loadDocs("Salinity")
