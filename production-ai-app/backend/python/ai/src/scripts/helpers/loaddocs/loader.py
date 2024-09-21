from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

import os
import json


# Function takes all files in the unloaded section and then puts them into a database
def loadFiles(databaseName: str = "Salinity"):
    load_dotenv()
    # sets OpenAI Embedder API
    openAiKey = os.getenv("OPENAI_API_KEY")

    embedder = OpenAIEmbeddings(
        api_key=openAiKey,
    )

    # Sets Directories to collect Files from
    docDirectory = "../../../projects/" + databaseName + "/docs/unloaded/"
    finalDirectory = "../../../projects/" + databaseName + "/docs/loaded/"

    # Gets Directory for Saving Databse
    databaseDirectory = "../../../projects/" + databaseName + "/data/database"

    # Grabs location for documents JSON to be stored in
    docListDirectory = "../../../projects/" + databaseName + "/data/documents.json"

    # Goes Through Each File in the Directory and adds it to database
    for i in os.listdir(docDirectory):

        # Loads in the Documents
        fileDir = docDirectory + i
        loader = TextLoader(fileDir)
        documents = loader.load()

        print(documents)

        # Split Documents
        splitter = RecursiveCharacterTextSplitter()
        splitData = splitter.split_documents(documents)

        # Appends Split Data into Database
        db = FAISS.from_documents(splitData, embedder)

        # Saves Individual Meeting Database
        db.save_local(databaseDirectory, i)

        # Appends Old Database to New One to Keep previous Documents
        if os.path.exists(databaseDirectory + "/team.faiss"):
            print("Database Merging")
            old_db = FAISS.load_local(
                databaseDirectory,
                embedder,
                "team",
                allow_dangerous_deserialization=True,
            )
            db.merge_from(old_db)
            print("Database Merged")
            
        # Saves Global Version of the Database`
        db.save_local(databaseDirectory, "main")
        print("Database Saved")

        # Moves file from Unloaded folder to loaded folder
        os.rename(fileDir, finalDirectory + i)

    # Adds Files Loaded into JSON

    if os.path.exists(docListDirectory):

        # Grabs Already Known Clients From JSON into List
        docFile = open(docListDirectory, "r")
        docs = json.load(docFile)
        docFile.close()

        # Appends New Clients to List of Clients
        docs = docs + os.listdir(docDirectory)

        # Removes Any Exact Duplicate Files
        docs = list(set(docs))

        # Puts New List of Clients Back into Array
        docFile = open(docListDirectory, "w")
        json.dump(docs, docFile)
        docFile.close()

    else:

        # Dumps New Client Data into JSON
        with open(docListDirectory, "w") as docFile:

            # Write some text to the file
            json.dump(os.listdir(docDirectory), docFile)


if __name__ == "__main__":
    loadFiles()