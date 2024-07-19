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

SOURCE_PDF_PATH = './data/airbnb.pdf'
SOURCE_PDF_NAME = "Airbnb 10-k Filings from Q1-2024"
VECTORSTORE_LOCATION = os.environ['QDRANT_VECTORSTORE_LOCATION']  # ':memory:'
VECTORSTORE_COLLECTION_NAME = 'reportwiz_store'

# -- RETRIEVAL -- #

# LOAD OpenAI EMBEDDINGS API object
#embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
embedding_model = AzureOpenAIEmbeddings(
    #model="text-embedding-3-small",
    azure_deployment=os.environ['AZURE_OPENAI_EMB_DEPLOYMENT'],
    openai_api_version="2023-05-15",
)

qdrant_vectorstore = None

# Let's check if the collection exists first.
# There's an API for it: https://api.qdrant.tech/api-reference/collections/collection-exists
# but it's not in the Python library (yet?),
# so I'll make the REST request directly and save the result in a variable
r = requests.get(f'{VECTORSTORE_LOCATION}/collections/{VECTORSTORE_COLLECTION_NAME}/exists',
                 headers={'api-key': qdrant_api_key}
                 )
collection_exists = r.json()['result']['exists']
# print(collection_exists)


if not collection_exists:
    print(f"Indexing Files into vectorstore {VECTORSTORE_COLLECTION_NAME}")

    # Load docs
    # CREATE TEXT LOADER AND LOAD DOCUMENTS
    # documents = PyMuPDFLoader(SOURCE_PDF_PATH).load()

    # convert the source PDF document to markdown, save it locally
    md_text = pymupdf4llm.to_markdown(SOURCE_PDF_PATH)
    md_path = SOURCE_PDF_PATH + '.md'
    pathlib.Path(md_path).write_bytes(md_text.encode())

    text_loader = TextLoader(md_path)
    documents = text_loader.load()

    # CREATE TEXT SPLITTER AND SPLIT DOCUMENTS
    text_splitter = MarkdownTextSplitter(  # RecursiveCharacterTextSplitter(
        chunk_size=600,
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