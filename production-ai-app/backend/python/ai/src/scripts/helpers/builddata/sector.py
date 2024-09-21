from langchain_openai import ChatOpenAI
from langchain.chains.openai_functions.openapi import get_openapi_chain
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Memory Based Imports Stores Messages
from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage
from langchain_core.messages import SystemMessage

import os
import csv
import json


# Createts a JSON to hold which Sector each client belongs to
def getSectors(projectName: str = "Default"):

    # Sets up all the API keys and objects to call ChatGPT
    openAiKey = os.environ.get("OPENAI_API_KEY")

    llm = ChatOpenAI(api_key=openAiKey, temperature=0)

    embeddings = OpenAIEmbeddings(
        api_key=openAiKey,
    )

    # Gets Directory of Clients JSON
    clientDir = "../projects/" + projectName + "/data/clients.json"

    # Opens and stores Client Array
    clientFile = open(clientDir, "r")
    clients = json.load(clientFile)
    clientFile.close()

    query = f"""You are a expert at identifying different sectors or industries of clients. \
    You will be given a list of clients and you are to do as follows. \
    Analyze the text they give you and give a sector for each . \
    Only give 1 sector per client
    The sectors should not be sentences
    Here is an example of the output format:
    
    client : sector
    
    Electrical Components Inc. : Technology
    Computers R Us : Technology
    Office of Departmental Organization : Adminstration
    Pretzel World : Food
    Executive Office : Adminstration
    Hotdog Stands United : Food
    Here is the following list of clients : {clients}\
    """

    # Generates proper query to categorize list of client and asks GPT to do it
    response = llm.invoke(query)
    response = response.content

    # Parses and cleans GPTs response to be able to get each clients Sector
    clientDepartments = response.replace("-", "").split("\n")
    for i, j in enumerate(clientDepartments):
        clientDepartments[i] = clientDepartments[i].strip()
        clientDepartments[i] = clientDepartments[i].split(":")
        clientDepartments[i][1] = clientDepartments[i][1].strip()

    # Creates a list of all sectors and removes duplicates
    sectors = [i[1] for i in clientDepartments]
    sectors = list(set(sectors))

    # Cleans Sector Data
    for index, sector in enumerate(sectors):
        sectors[index] = sectors[index].strip()

    # Creates dictionary and has sector index to be able to call each sector in use
    clientSector = {}
    clientSector["sectors"] = sectors

    # Creates Declares an empty array for each sector
    for i in sectors:
        clientSector[i] = []

    # Puts Each Client into their respective sector
    for i in clientDepartments:
        clientSector[i[1]].append(i[0].strip())

    # Sets Directory for Sector JSON
    sectorDir = "../projects/" + projectName + "/data/sector.json"

    # Stores all the data into the sector directory
    sectorFile = open(sectorDir, "w")
    json.dump(clientSector, sectorFile)
    sectorFile.close()
