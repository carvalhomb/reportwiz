import os
import requests
import dotenv
import pathlib
import operator
import ast

import chainlit as cl

import pymupdf4llm

from qdrant_client import QdrantClient

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

#from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI,  AzureOpenAIEmbeddings
#from langchain_openai.embeddings import OpenAIEmbeddings

from langchain_community.document_loaders import TextLoader  # , PyMuPDFLoader
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_community.tools.arxiv.tool import ArxivQueryRun

from langchain_text_splitters import MarkdownTextSplitter, RecursiveCharacterTextSplitter

from langchain_community.vectorstores import Qdrant

from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import Runnable, RunnablePassthrough
from langchain.schema.runnable.config import RunnableConfig

from langchain_core.utils.function_calling import convert_to_openai_function
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)

from langchain.agents import tool, AgentExecutor
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.tools import StructuredTool





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
#rag_prompt = ChatPromptTemplate.from_template(RAG_PROMPT)


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a not very knowleadgeable  assistant. You are bad at calculating lengths of words.",
        ),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# -- GENERATION -- #
"""
1. Access ChatGPT API
"""

#openai_chat_model = ChatOpenAI(model="gpt-4o", streaming=True)


llm = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


@tool
def get_word_length(word: str) -> int:
    """Returns the length of a word."""
    return len(word)+5


tool_belt = [
    #DuckDuckGoSearchRun(),
    #ArxivQueryRun(),
    get_word_length
]


tools = [convert_to_openai_function(t) for t in tool_belt]

model_with_tools = llm.bind_tools(tools)


# lcel = (
#     {
#         "input": lambda x: x["input"],
#         "agent_scratchpad": lambda x: format_to_openai_tool_messages(
#             x["intermediate_steps"]
#         ),
#     }
#     | prompt
#     | model_with_tools
#     | OpenAIToolsAgentOutputParser()
    
# )

# agent_executor = AgentExecutor(agent=agent, tools=tool_belt, verbose=True)
from langchain_core.messages import HumanMessage


from langgraph.prebuilt import create_react_agent

agent_executor = create_react_agent(model_with_tools, tools)

response = agent_executor.invoke({"messages": [HumanMessage(content="How many letters in the word eudca")]})

print(response["messages"])
print(response)



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
    cl.user_session.set("agent_executor", agent_executor)



@cl.on_message
async def main(message: cl.Message):
    """
    This function will be called every time a message is received from a session.

    We will use the LCEL RAG chain to generate a response to the user query.

    The LCEL RAG chain is stored in the user session, and is unique to each user session - this is why we can access it here.
    """
    agent_executor = cl.user_session.get("agent_executor")

    cb = cl.AsyncLangchainCallbackHandler(#stream_final_answer=True
        )
    #cb = cl.LangchainCallbackHandler()
    myconfig = RunnableConfig(callbacks=[cb])

    msg = cl.Message(content="")

    # async for chunk in agent_executor.astream(
    #         {"query": message.content},
    #         config=myconfig,
    # ):
    #     await msg.stream_token(chunk)

    # await msg.send()

    res = await agent_executor.ainvoke(
        {"input": message.content}, 
        #callbacks=[cl.AsyncLangchainCallbackHandler()]
        config=myconfig
    )

    await cl.Message(content=res).send()