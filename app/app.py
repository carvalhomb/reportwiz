import os
import requests
import dotenv
import pathlib
import operator

import chainlit as cl

import pymupdf4llm

from qdrant_client import QdrantClient

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

#from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI,  AzureOpenAIEmbeddings
#from langchain_openai.embeddings import OpenAIEmbeddings

from langchain_community.document_loaders import TextLoader  # , PyMuPDFLoader
from langchain_text_splitters import MarkdownTextSplitter, RecursiveCharacterTextSplitter

from langchain_community.vectorstores import Qdrant

from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import Runnable, RunnablePassthrough
from langchain.schema.runnable.config import RunnableConfig

# GLOBAL SCOPE - ENTIRE APPLICATION HAS ACCESS TO VALUES SET IN THIS SCOPE #
# ---- ENV VARIABLES ---- #
"""
This function will load our environment file (.env) if it is present.
Our OpenAI API Key lives there and will be loaded as an env var
here: os.environ["OPENAI_API_KEY"]
"""
dotenv.load_dotenv()

qdrant_api_key = os.environ["QDRANT_API_KEY"]

# ---- GLOBAL DECLARATIONS ---- #
ASSISTANT_NAME = "ReportWiz"
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
qdrant_retriever = qdrant_vectorstore.as_retriever()

# -- AUGMENTED -- #
"""
1. Define a String Template
2. Create a Prompt Template from the String Template
"""
### 1. DEFINE STRING TEMPLATE
RAG_PROMPT = """
CONTEXT:
{context}

QUERY:
{query}

Use the provide context to answer the provided user query. 
Only use the provided context to answer the query. 
If the query is unrelated to the context given, you should apologize and answer 
that you don't know because it is not related to the "Airbnb 10-k Filings from Q1, 2024" document.
"""

# CREATE PROMPT TEMPLATE
rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT)

# -- GENERATION -- #
"""
1. Access ChatGPT API
"""

#openai_chat_model = ChatOpenAI(model="gpt-4o", streaming=True)


openai_chat_model = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


@cl.author_rename
def rename(original_author: str):
    """
    This function can be used to rename the 'author' of a message.
.
    """
    rename_dict = {
        "Assistant": ASSISTANT_NAME,
        "Chatbot": ASSISTANT_NAME,
    }
    return rename_dict.get(original_author, original_author)


@cl.on_chat_start
async def start_chat():
    lcel_rag_chain = (
            {
                "context": operator.itemgetter("query") | qdrant_retriever,
                "query": operator.itemgetter("query")
            }
            | rag_prompt | openai_chat_model | StrOutputParser()
    )

    cl.user_session.set("lcel_rag_chain", lcel_rag_chain)


@cl.on_message
async def main(message: cl.Message):
    """
    This function will be called every time a message is received from a session.

    We will use the LCEL RAG chain to generate a response to the user query.

    The LCEL RAG chain is stored in the user session, and is unique to each user session - this is why we can access it here.
    """
    lcel_rag_chain = cl.user_session.get("lcel_rag_chain")

    msg = cl.Message(content="")

    async for chunk in lcel_rag_chain.astream(
            {"query": message.content},
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)

    await msg.send()

