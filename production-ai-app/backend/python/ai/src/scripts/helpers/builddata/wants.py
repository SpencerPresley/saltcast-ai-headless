from langchain_openai import ChatOpenAI
from langchain.chains.openai_functions.openapi import get_openapi_chain
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import os
import csv
import json


def getWants(databaseName: str = "Default"):

    # Opens up LLM Objects
    openAiKey = os.environ.get("OPENAI_API_KEY")

    llm = ChatOpenAI(api_key=openAiKey, temperature=0)

    embeddings = OpenAIEmbeddings(
        api_key=openAiKey,
    )

    # Gets Open the Cumulative Database
    new_db = FAISS.load_local(
        "../projects/" + databaseName + "/data/database",
        embeddings,
        "main",
        allow_dangerous_deserialization=True,
    )

    # Gets Client List Location
    clientDir = "../projects/" + databaseName + "/data/clients.json"
    wantsDir = "../projects/" + databaseName + "/data/wants.json"

    # Declares Dictionary to store client wants into
    clientWants = {}

    # Gets List of Clients and puts it into dictionary
    clientFile = open(clientDir, "r")
    clients = json.load(clientFile)
    clientWants["clients"] = clients
    clientFile.close()

    # Goes through each client and grabs relevant issues to them
    for client in clients:

        # Constructs Prompt Based on data from database
        prompt = f"list of the the issues faced by {client}"
        docs = new_db.similarity_search(prompt)

        prompt = f"""You are a expert at identifying issues faced by a certain client. \                                                                                                 
    You will be given a sections of documents and you are to do as follows. \                                                                                                                       
    Analyze the given text and return a cumulative list of all the problems faced by {client}. \ 
    The clients should not be long sentences                                                                                                                                                       
    Here is an example of the output format:                                                                                                                                                  
                                                                                                                                                                                             
    - client                                                                                                                                                                           
                                                                                                                                                                                           
    - Rising Financial Constraints                                                                                                                                                 
    - Website Needs Dashboard                                                                                                                                                           
    - Additional Visuals Needed
    - Background Reds should be swapped to blues

     Here are the documents:
     {docs}
    """

        # Gets Response List from GPT
        response = llm.invoke(prompt)

        # Formats Response into an array
        problems = response.content.replace("-", "").split("\n")
        for i, j in enumerate(problems):
            problems[i] = problems[i].strip()

        # Adds Clients to Dictionary
        clientWants[client] = problems

    # Puts Dictionary into JSON
    wantFile = open(wantsDir, "w")
    json.dump(clientWants, wantFile)
    wantFile.close()
