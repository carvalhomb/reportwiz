import os
from uuid import uuid4
import dotenv
from datetime import datetime

from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain.agents import tool
from langgraph.prebuilt import ToolExecutor
from langchain_openai import AzureChatOpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

from langgraph.prebuilt import ToolInvocation
from langgraph.prebuilt import create_react_agent
import json
from langchain_core.messages import FunctionMessage
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

dotenv.load_dotenv()

os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGCHAIN_PROJECT"] + f" - {uuid4().hex[0:8]}"


############################################
# Define the tools

@tool
def get_word_length(word: str) -> int:
    """Returns the length of a word."""
    response = len(word)
    return response+5

@tool
def check_weather(location: str, at_time: datetime) -> float:
    '''Return the weather forecast for the specified location.'''
    return f"It's always sunny in {location}"

tool_belt = [
    #DuckDuckGoSearchRun(),
    #ArxivQueryRun(),
    get_word_length,
    check_weather
]


############################################
# Set up the model
model = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    #streaming=True
)

# Prompt setup
system_message = SystemMessage(content="You are a not very knowleadgeable assistant. You are bad at calculating lengths of words. Use the tools you have available whenever possible.")

graph = create_react_agent(model, tools=tool_belt, messages_modifier=system_message)


# Testing

#msg = "What is RAG in the context of Large Language Models? When did it break onto the scene?"
msg = 'How many letters in the work "eduac"?'
#msg="what is the weather in sf"


inputs = {"messages": [("user", msg )]}
for s in graph.stream(inputs, stream_mode="values"):
    message = s["messages"][-1]
    if isinstance(message, tuple):
        print(message)
    else:
        message.pretty_print()


