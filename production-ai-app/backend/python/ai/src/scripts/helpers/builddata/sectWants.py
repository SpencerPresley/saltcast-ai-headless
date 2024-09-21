import json


# Takes the JSON of Client Wants and The JSON of which Sector a client Belongs to to create a JSON of what each sector wants
def getSectorWants(projectName: str = "Default"):

    # Gets Files Directories of Needed JSONs
    clientDir = "../projects/" + projectName + "/data/wants.json"
    sectorDir = "../projects/" + projectName + "/data/sector.json"

    # Opens and grabs Dictionary from previous JSONs
    clientFile = open(clientDir, "r")
    clients = json.load(clientFile)
    clientFile.close()

    sectorFile = open(sectorDir, "r")
    sectors = json.load(sectorFile)
    sectorFile.close()

    # Creates a dictionary to hold each sector wants
    sectorWants = {}

    # stores sectors for retrivival
    sectorWants["sectors"] = sectors["sectors"]

    # Assigns all values to dictionary
    for sector in sectors["sectors"]:
        sectorWants[sector] = []
        for client in sectors[sector]:
            for want in clients[client]:
                sectorWants[sector].append(want)

    # Gets Directory to put dictionary data into
    sectorWantsDir = "../projects/" + projectName + "/data/sectorWants.json"

    # Creates the JSON and Stores Dictionary Data inside of it
    with open(sectorWantsDir, "w") as sectorWantsFile:
        # Write some text to the file
        json.dump(sectorWants, sectorWantsFile)

    sectorWantsFile.close()
