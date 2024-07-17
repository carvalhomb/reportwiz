import os
import dotenv
import pathlib
import operator
import ast
import uuid

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

    # Save the list in the session to store the message history
    cl.user_session.set("inputs", {"messages": []})

    # Create a thread id and pass it as configuration
    #config = {"metadata": {"conversation_id": str(uuid.uuid4())}}
    conversation_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conversation_id}}
    cl.user_session.set("config", config)

@cl.on_message
async def main(msg: cl.Message):
    """
    This function will be called every time a message is received from a session.
    """

    # msg is the user message,
    # agent_message is the agents.


    #graph: Runnable = cl.user_session.get("graph")
    graph = cl.user_session.get("graph")
    config = cl.user_session.get("config")

    inputs = {"messages": [("user", msg.content)]}

    agent_message = cl.Message(content="")
    await agent_message.send()

    # events = []
    # async for event in graph.astream_events(inputs, version="v2", config=config):
    #     events.append(event)

    # print(events)
    async for event in graph.astream_events(inputs, version="v2", config=config):
        kind = event["event"]
        #print(kind)
        if kind == "on_chain_start":
            if (
                event["name"] == "Agent"
            ):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
                print(
                    f"Starting agent: {event['name']} with input: {event['data'].get('input')}"
                )
        elif kind == "on_chain_end":
            if (
                event["name"] == "Agent"
            ):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
                print()
                print("--")
                print(
                    f"Done agent: {event['name']} with output: {event['data'].get('output')['output']}"
                )
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Empty content in the context of OpenAI means
                # that the model is asking for a tool to be invoked.
                # So we only print non-empty content
                #print(content, end="|")

                await agent_message.stream_token(content)

        elif kind == "on_tool_start":
            print("--")
            print(
                f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
            )
        elif kind == "on_tool_end":
            print(f"Done tool: {event['name']}")
            print(f"Tool output was: {event['data'].get('output')}")
            print("--")


    # Send empty message to stop the little ball from blinking
    await agent_message.send()