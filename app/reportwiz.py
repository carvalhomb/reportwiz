import os
import dotenv

import json



from langchain_openai import AzureChatOpenAI
from typing import Annotated, Literal
from typing_extensions import TypedDict



from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, ToolMessage, AnyMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langgraph.checkpoint import MemorySaver

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

from langchain_core.runnables.graph import MermaidDrawMethod

from typing import List
from enum import Enum

from langchain_core.pydantic_v1 import BaseModel, Field



from info_retriever import runnable_retriever, retriever_tool_belt


dotenv.load_dotenv()

VERSION = '0.7'
os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGCHAIN_PROJECT"] + f" - v. {VERSION}"




################################################
# CREATE THE GRAPH MANUALLY

# # Create a chain with the main prompt and the llm bound with tools
# primary_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system", main_prompt
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# )
# chat_runnable = primary_prompt | llm_chatbot



#----------------------------------------
# Define nodes

def retriever(state: MessagesState):
    return {"messages": [runnable_retriever.invoke(state["messages"])]}

def route_tools(
    state: MessagesState,
) -> Literal["tools", "__end__"]:
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"

retriever_tool_node = ToolNode(tools=retriever_tool_belt)

#----------------------------------------
# Build the graph, connecting the edges

# Start the graph
graph_builder = StateGraph(MessagesState)

# Add the nodes
graph_builder.add_node("retriever", retriever)
graph_builder.add_node("retriever_tools", retriever_tool_node)

# Add the edges
graph_builder.add_edge(START, "retriever")

# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "__end__" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "retriever",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "retriever_tools", "__end__": "__end__"},
)

# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("retriever_tools", "retriever")


# Add memory to the agent using a checkpointer
graph = graph_builder.compile(checkpointer=MemorySaver())




graph.get_graph().print_ascii()
# png_graph = graph.get_graph().draw_mermaid_png(
#             draw_method=MermaidDrawMethod.API,
#         )

# graph_path = '/mnt/c/Users/mbrandao/Downloads/graph.png'
# #graph_path = 'graph.png'
# with open(graph_path, 'wb') as png_file:
#     png_file.write(png_graph)

#from langchain_core.messages import HumanMessage

# import uuid
# conversation_id = str(uuid.uuid4())
# config = {"configurable": {"thread_id": conversation_id}}

# inputs = {"messages" : [HumanMessage(content="What is the weather like in Brasilia, Brazil?")]}

# messages = graph.invoke(inputs, config=config,)