from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import os
import shutil
import json
from docx import Document
import pandas as pd
import re


def formatCSVFile(sectorStats: str = "Default"):
    linesRemove = []
    lines = sectorStats.splitlines()

    # finds all lines with NaN
    for index, line in enumerate(lines):

        if "NaN" in line:
            linesRemove.append(index)

    lines = [j for i, j in enumerate(lines) if i not in linesRemove]  # Removes lines
    sectorStats = "\n".join(lines)  # Turns all the lines with No Nan to string
    sectorStats = re.sub(
        r"[\t\r\f\v ]+", " ", sectorStats.strip()
    )  # Gets rid of absurd amount of spacing
    return sectorStats


def docxToTxt(fileDir: str = "Default"):
    fileName = fileDir.replace(".docx", "")
    document = Document(fileDir)

    f = open(fileName + ".txt", "a")

    for paragraph in document.paragraphs:
        f.write(paragraph.text)
        f.write("\n")

    f.close()


def csvToTxt(docDirectory: str = "Default"):

    fileName = docDirectory.replace(".csv", "")

    # docDirectory = '../projects/Salinity/docs/unloaded/Maryland_Tidal_Locations_ShortList_Version2_ziyu.csv'
    df = pd.read_csv(docDirectory)

    df = df.dropna(how="all")

    CSVDataArr = []

    for csvIndex in range(len(df)):

        indexData = df.iloc[csvIndex].to_string()
        indexData = formatCSVFile(indexData)
        CSVDataArr.append(indexData)

    data = "\n\n".join(CSVDataArr)

    f = open(fileName + ".txt", "a")
    f.write(data)
    f.close()


def convertFiles(projectName: str = "Default"):
    directory = "../projects/" + projectName + "/docs/unloaded/"
    for i in os.listdir(directory):
        if ".csv" in i:
            csvToTxt(directory + i)
            shutil.move(directory + i, directory + "../loaded")

        if ".docx" in i:
            docxToTxt(directory + i)
            shutil.move(directory + i, directory + "../loaded")
