import os
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
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langgraph.graph import StateGraph, END


from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessage


import operator

from reportwiz import graph




ASSISTANT_NAME = "ReportWiz"




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
    
    cl.user_session.set("graph", graph)



@cl.on_message
async def main(message: cl.Message):
    """
    This function will be called every time a message is received from a session.
    """
    graph: Runnable = cl.user_session.get("graph")

    state = cl.user_session.get("state")
    #messages = state['messages']

    # res = await graph.arun(
    #     message.content, callbacks=[cl.AsyncLangchainCallbackHandler()]
    # )
    # await cl.Message(content=res).send()

    # Currently functions, without steps
    res = await cl.make_async(graph.invoke)({"keys": {"question": message.content}}, stream_mode="values")

    #content = message.content

    #state = cl.user_session.get("state")

    # Append the new message to the state
    #state["messages"] += [HumanMessage(content=message.content)]


    # Stream the response to the UI
    # ui_message = cl.Message(content="")
    # await ui_message.send()
    # async for event in graph.astream_events(state, version="v1"):

    #     if event["event"] == "on_chain_stream" and event["name"] == "agent":
    #         content = event["data"]["chunk"]['messages'][0].content or ""
    #         await ui_message.stream_token(token=content)
    # await ui_message.update()

    # for s in graph.stream(inputs, stream_mode="values"):
    # message = s["messages"][-1]
    # if isinstance(message, tuple):
    #     print(message)
    # else:
    #     message.pretty_print()




