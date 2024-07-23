import os
import dotenv
import pathlib

from langchain_openai import AzureOpenAIEmbeddings
import pymupdf4llm
from qdrant_client import QdrantClient

from langchain_community.document_loaders import TextLoader 
from langchain_text_splitters import MarkdownTextSplitter
from langchain_qdrant import QdrantVectorStore

from langchain.agents import tool

dotenv.load_dotenv()

qdrant_api_key = os.environ["QDRANT_API_KEY"]

# ---- GLOBAL DECLARATIONS ---- #

PDF_FOLDER_PATH = "data/reports/"
VECTORSTORE_LOCATION = os.environ["QDRANT_VECTORSTORE_LOCATION"]
VECTORSTORE_COLLECTION_NAME = os.environ['LANGCHAIN_PROJECT']

# -- RETRIEVAL -- #

# LOAD OpenAI EMBEDDINGS API object
embedding_model = AzureOpenAIEmbeddings(
    azure_deployment=os.environ['AZURE_OPENAI_EMB_DEPLOYMENT'],
    openai_api_version="2023-05-15",
)

docs_path = pathlib.Path(PDF_FOLDER_PATH)


qdrant_vectorstore = None

qdrant_client = QdrantClient(url=VECTORSTORE_LOCATION, api_key=qdrant_api_key)

collection_exists = qdrant_client.collection_exists(collection_name=VECTORSTORE_COLLECTION_NAME)


if not collection_exists:
    print(f"Indexing Files into vectorstore {VECTORSTORE_COLLECTION_NAME}")

    # Load docs

    # convert the source PDF document to markdown, save it locally
    source_documents = []
    for file in docs_path.glob("*.pdf"):

        md_text = pymupdf4llm.to_markdown(file)

        md_path = file.with_suffix('.md')
        md_path.write_bytes(md_text.encode())

        text_loader = TextLoader(md_path)
        loaded_doc = text_loader.load()[0]
        loaded_doc.metadata['source'] = file.name
        source_documents.append(loaded_doc)


    # CREATE TEXT SPLITTER AND SPLIT DOCUMENTS
    text_splitter = MarkdownTextSplitter(  # RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=20,
    )

    split_documents = text_splitter.split_documents(source_documents)

    # INDEX FILES
    qdrant_vectorstore = QdrantVectorStore.from_documents(
        split_documents,
        embedding = embedding_model,
        location=VECTORSTORE_LOCATION,
        collection_name=VECTORSTORE_COLLECTION_NAME,
        prefer_grpc=True,
        api_key=qdrant_api_key,
    )

else:
    # Load existing collection
    qdrant_vectorstore = QdrantVectorStore.from_existing_collection(
        embedding=embedding_model,
        collection_name=VECTORSTORE_COLLECTION_NAME,
        url=VECTORSTORE_LOCATION,
        prefer_grpc=True,
        api_key=qdrant_api_key,
    )


# Create the retriever
# qdrant_retriever = qdrant_vectorstore.as_retriever(
#     search_type='similarity_score_threshold',
#     search_kwargs={'score_threshold': 0.5, 'k': 3}
# )

# # Create the tool
# pdf_retriever = create_retriever_tool(
#     qdrant_retriever,
#     "retrieve_pdfs",
#     ,
# )

@tool
def pdf_retriever(user_query):
    """
    Tool to search and return reports from existing reports database. 
    These reports are the preferred way of giving the user information about
    the weather in Croatia, and how the weather affects solar panel electricity 
    production and usage.
    """
    hits = qdrant_vectorstore.similarity_search_with_score(user_query, k=3, score_threshold=0.5)
    #return hits
    responses = []

    for doc, score in hits:
        response = {}

        response['source_documents'] = doc.metadata['source']
        response['contents'] = doc.page_content

        responses.append(response)

    return responses



