from langchain_openai import ChatOpenAI
from langchain.chains.openai_functions.openapi import get_openapi_chain
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage
from langchain_core.messages import SystemMessage

import os
import csv
import json


# Function Used for appending Interview Clients to Client JSON
def getClients(projectName: str = "Default", meetingName: str = "Default"):

    # Sets up LLM API
    openAiKey = os.environ.get("OPENAI_API_KEY")

    llm = ChatOpenAI(api_key=openAiKey, temperature=0)

    embeddings = OpenAIEmbeddings(api_key=openAiKey)

    # Opens Database for Meeting
    new_db = FAISS.load_local(
        "../projects/" + projectName + "/data/database",
        embeddings,
        meetingName,
        allow_dangerous_deserialization=True,
    )

    # Constructs Prompt Based on data from database
    prompt = "Give me a bullet point list of the organizations and departments speaking in this meeting please do not list any individuals"
    docs = new_db.similarity_search(prompt)

    # Generates System Prompt
    chatHistory = [
        SystemMessage(
            """
    Your Job is to read various meeting documents and identify the organizations participating in the meeting \
    You will be given a sections of documents and you are to do as follows. \                                                                                                                       

    Identify which organizations we know for certain have representative participating in the meeting \
            Never list individual people or there name instead only organizations and departments that have representives in the meeting This data need to all be anonymous so no references to people
    Do not list organizations not directly involved in the meeting only ones directly participating for in meeting
    Do not feel need to overlist the amount of organizations
    Do not use information in the system prompt section

    Clients are Organizations Buisnesses Departments or any sort of collection of peoples that have stakeholdership in the interview and have a representative acting in the meeting
    The clients should not be listed in sentences
    Here is an example of the output format although their may be significantly fewer or more than presented here reduce and enlarge number of clients accordingly:
                                                                                                                                                                                             
    - client                                                                                                                                                                           
                                                                                                                                                                                           
    - Electrical Components Inc.                                                                                                                                                 
    - Computers R Us                                                                                                                                                           
    - Office of Departmental Organization                                                                                                                                      
    - Pretzel World                                                                                                                                                                      
    - Executive Office                                                                                                                                                         
    - Hotdog Stands United         
    """
        )
    ]

    # Gives Documents to GPT
    prompt = f"""
    documents:
    {docs}
    """

    # Adds True Document to History
    chatHistory.append(HumanMessage(content=prompt))

    # Calls ChatGPT for Response
    response = llm.invoke(chatHistory)

    # Parses GPTs Response and Cleans it and Lightly Formats it
    departments = response.content.replace("-", "").split("\n")
    for i, j in enumerate(departments):
        departments[i] = departments[i].strip()
        departments[i] = departments[i].upper()

    # Grabs location for client JSON to be stored in
    clientDir = "../projects/" + projectName + "/data/clients.json"

    # Identifies if Client Data has been Created yet if so Opens it if not Creates it
    if os.path.exists(clientDir):

        # Grabs Already Known Clients From JSON into List
        clientFile = open(clientDir, "r")
        clients = json.load(clientFile)
        clientFile.close()

        # Appends New Clients to List of Clients
        clients = clients + departments

        # Removes Any Exact Duplicate Clients
        clients = list(set(clients))

        # Puts New List of Clients Back into Array
        clientFile = open(clientDir, "w")
        json.dump(clients, clientFile)
        clientFile.close()

    else:

        # Dumps New Client Data into JSON
        with open(clientDir, "w") as clientFile:

            # Write some text to the file
            json.dump(departments, clientFile)


def getAllClients(projectName: str = "Default"):

    # Gets Client Directory Location
    clientDir = "../projects/" + projectName + "/data/clients.json"

    # Grabs List of All the Files to get Clients From
    meetDir = "../projects/" + projectName + "/data/documents.json"

    # Deletes Client Directory to start from scratch
    if os.path.exists(clientDir):
        os.remove(clientDir)

    meetFile = open(meetDir, "r")
    meetings = json.load(meetFile)
    meetFile.close()

    # Loops Through Every meeting to get Clients
    for i in meetings:
        getClients(projectName, i)


getAllClients("Salinity")
