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




from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
import operator
from langchain_core.messages import BaseMessage

from langgraph.prebuilt import ToolInvocation
import json
from langchain_core.messages import FunctionMessage


# GLOBAL SCOPE - ENTIRE APPLICATION HAS ACCESS TO VALUES SET IN THIS SCOPE #
# ---- ENV VARIABLES ---- #
"""
This function will load our environment file (.env) if it is present.
Our OpenAI API Key lives there and will be loaded as an env var
here: os.environ["OPENAI_API_KEY"]
"""



ASSISTANT_NAME = "ReportWiz"



# -- AUGMENTED -- #
"""
1. Define a String Template
2. Create a Prompt Template from the String Template
"""
### 1. DEFINE STRING TEMPLATE
# RAG_PROMPT = """
# CONTEXT:
# {context}

# QUERY:
# {query}

# Use the provide context to answer the provided user query. 
# Only use the provided context to answer the query. 
# If the query is unrelated to the context given, you should apologize and answer 
# that you don't know because it is not related to the "Airbnb 10-k Filings from Q1, 2024" document.
# """

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


model = AzureChatOpenAI(
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
    response = len(word)+5
    return response


tool_belt = [
    DuckDuckGoSearchRun(),
    ArxivQueryRun(),
    get_word_length
]


tool_executor = ToolExecutor(tool_belt)


functions = [convert_to_openai_function(t) for t in tool_belt]

model = model.bind_tools(functions)


class AgentState(TypedDict):
  messages: Annotated[list, add_messages]


def call_model(state):
  messages = state["messages"]
  response = model.invoke(messages)
  return {"messages" : [response]}

def call_tool(state):
  last_message = state["messages"][-1]

  action = ToolInvocation(
      tool=last_message.additional_kwargs["function_call"]["name"],
      tool_input=json.loads(
          last_message.additional_kwargs["function_call"]["arguments"]
      )
  )

  response = tool_executor.invoke(action)

  function_message = FunctionMessage(content=str(response), name=action.tool)

  return {"messages": [function_message]}





def should_continue(state):
  last_message = state["messages"][-1]

  if "function_call" not in last_message.additional_kwargs:
    return "end"

  return "continue"




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
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("action", call_tool)
    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "end": END
        }
    )
    workflow.add_edge("action", "agent")

    # initialize state
    state = AgentState(messages=[])

    app = workflow.compile()
    cl.user_session.set("workflow", app)

    workflow.get_graph().print_ascii()

    cl.user_session.set("state", state)



@cl.on_message
async def main(message: cl.Message):
    """
    This function will be called every time a message is received from a session.
    """
    workflow: Runnable = cl.user_session.get("workflow")
    state = cl.user_session.get("state")

    # Append the new message to the state
    state["messages"] += [HumanMessage(content=message.content)]

    import pprint
    # Stream the response to the UI
    ui_message = cl.Message(content="")
    await ui_message.send()
    async for event in workflow.astream_events(state, version="v1"):
        pprint.pprint(event)
        if event["event"] == "on_chain_stream" and event["name"] == "agent":
            content = event["data"]["chunk"]['messages'][0].content or ""
            await ui_message.stream_token(token=content)
    await ui_message.update()