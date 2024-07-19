import os
import dotenv
import requests
import operator
import pathlib

from langchain_openai import AzureOpenAIEmbeddings
import pymupdf4llm
from qdrant_client import QdrantClient

from langchain_community.document_loaders import TextLoader  # , PyMuPDFLoader
from langchain_text_splitters import MarkdownTextSplitter
from langchain_community.vectorstores import Qdrant

from langchain.agents import tool


dotenv.load_dotenv()

qdrant_api_key = os.environ["QDRANT_API_KEY"]

# ---- GLOBAL DECLARATIONS ---- #

PDF_FOLDER_PATH = "data/reports/"
VECTORSTORE_LOCATION = os.environ["QDRANT_VECTORSTORE_LOCATION"]
VECTORSTORE_COLLECTION_NAME = os.environ['LANGCHAIN_PROJECT']

# -- RETRIEVAL -- #

# LOAD OpenAI EMBEDDINGS API object
#embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
embedding_model = AzureOpenAIEmbeddings(
    #model="text-embedding-3-small",
    azure_deployment=os.environ['AZURE_OPENAI_EMB_DEPLOYMENT'],
    openai_api_version="2023-05-15",
)

qdrant_vectorstore = None

qdrant_client = QdrantClient(url=VECTORSTORE_LOCATION, api_key=qdrant_api_key)

collection_exists = qdrant_client.collection_exists(collection_name=VECTORSTORE_COLLECTION_NAME)

if not collection_exists:
    print(f"Indexing Files into vectorstore {VECTORSTORE_COLLECTION_NAME}")

    # Load docs
    # CREATE TEXT LOADER AND LOAD DOCUMENTS
    # documents = PyMuPDFLoader(SOURCE_PDF_PATH).load()

    # convert the source PDF document to markdown, save it locally

    documents = []
    for file in os.listdir(PDF_FOLDER_PATH):
        if file.endswith('.pdf'):
                    
            md_text = pymupdf4llm.to_markdown(PDF_FOLDER_PATH  + file)

            md_path = PDF_FOLDER_PATH  + file + '.md'

            pathlib.Path(md_path).write_bytes(md_text.encode())

            text_loader = TextLoader(md_path)

            documents.extend(text_loader.load())

    # CREATE TEXT SPLITTER AND SPLIT DOCUMENTS
    text_splitter = MarkdownTextSplitter(  # RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=30,
        # length_function = tiktoken_len,
    )

    split_documents = text_splitter.split_documents(documents)
    # print(len(split_documents))

    # INDEX FILES
    qdrant_vectorstore = Qdrant.from_documents(
        split_documents,
        embedding_model,
        location=VECTORSTORE_LOCATION,
        collection_name=VECTORSTORE_COLLECTION_NAME,
        prefer_grpc=True,
        api_key=qdrant_api_key,
    )

else:
    # Load existing collection
    qdrant_vectorstore = Qdrant.from_existing_collection(
        embedding_model,
        path=None,
        collection_name=VECTORSTORE_COLLECTION_NAME,
        url=VECTORSTORE_LOCATION,
        prefer_grpc=True,
        api_key=qdrant_api_key,
    )


# Create the retriever
#qdrant_retriever = qdrant_vectorstore.as_retriever()

@tool
def pdf_retriever():
    """
    Tool to check a PDF repository of reports that have already been produced
    and are available for consultation by the user.
    """
    return 'There are no PDF reports in the repository that answer to the query.'