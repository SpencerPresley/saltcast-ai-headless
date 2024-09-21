from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

import os
import json


def mergeDatabases(
    databaseName: str = "Default",
    newIndexName: str = "Default",
    meetingsFile: str = "mergeDocs.json",
):

    # Sets up Embeedding eagent for Database Usage
    openAiKey = os.environ.get("OPENAI_API_KEY")

    embeddings = OpenAIEmbeddings(
        api_key=openAiKey,
    )

    # Gets Directory for Saving Databse
    databaseDirectory = "../projects/" + databaseName + "/data/database"

    # Grabs location for documents JSON to be stored in
    docListDirectory = "../projects/" + databaseName + "/data/" + meetingsFile

    # Grabs Already Known Clients From JSON into List
    docFile = open(docListDirectory, "r")
    docs = json.load(docFile)
    docFile.close()

    # Creates the database to store
    for i, j in enumerate(docs):

        # Creates Intial Databse
        if i == 0:
            db = FAISS.load_local(
                databaseDirectory, embeddings, j, allow_dangerous_deserialization=True
            )

        # Appends Extra Databases on top
        else:
            newDb = FAISS.load_local(
                databaseDirectory, embeddings, j, allow_dangerous_deserialization=True
            )
            db.merge_from(newDb)

    db.save_local(databaseDirectory, newIndexName)


mergeDatabases("Salinity", "MergeTest", "newDB.json")
