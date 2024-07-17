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
    #graph: Runnable = cl.user_session.get("graph")

        # When a message is received, get the agent and message history from session
    app = cl.user_session.get("graph")
    inputs = cl.user_session.get("inputs")
    config = cl.user_session.get("config")

    attachment_file_text = ""

    for element in msg.elements:
        #attachment_file_text += f"- {element.name} (path: {})\n"
        new_path = element.path.replace("/workspace", ".")
        attachment_file_text += f"{element.name} (path: {new_path})"
    
    content = msg.content
    
    if attachment_file_text:
        content += f"\n\n Attachments\n{attachment_file_text}"

    # Add user's message to history
    inputs["messages"].append(HumanMessage(content=content))

    # Send an empty message to prepare a place for streaming
    agent_message = cl.Message(content="")
    await agent_message.send()
    
    chunks = []

    # Run the agent
    # Many thanks to whoever wrote this: https://github.com/0msys/langgraph-chainlit-agent/blob/main/main.py
    async for output in app.astream_log(inputs, include_types=["llm"], config=config):
        for op in output.ops:
            if op["path"] == "/streamed_output/-":
                # Display progress in each step
                edge_name = list(op["value"].keys())[0]
                message = op["value"][edge_name]["messages"][-1]
                
                # In case of an action node, the message content is displayed (the return value of the tool is displayed)
                if edge_name == "action":
                    step_name = message.name
                    step_output = "```\n" + message.content + "\n```"

                # For agent nodes, if it is a function call, show the function name and arguments
                elif hasattr(message, "additional_kwargs") and message.additional_kwargs:
                    step_name = edge_name
                    fcall_name = message.additional_kwargs["function_call"]["name"]
                    fcall_addargs = message.additional_kwargs["function_call"]["arguments"]
                    step_output = f"function call: {fcall_name}\n\n```\n{fcall_addargs}\n```"
                
                # For other patterns nothing is displayed
                else:
                    continue

                # Submit step
                async with cl.Step(name=step_name) as step:
                    step.output = step_output
                    await step.update()

            elif op["path"].startswith("/logs/") and op["path"].endswith(
                "/streamed_output_str/-"
            ):
                # Stream the final response to a pre-prepared message
                chunks.append(op["value"])
                await agent_message.stream_token(op["value"])

        # Combine the streamed responses to create the final response
        res = "".join(chunks)

    # Add the final response to the history and save it in the session
    inputs["messages"].append(AIMessage(content=res))
    cl.user_session.set("inputs", inputs)

    await agent_message.update()
