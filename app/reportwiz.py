import os
import dotenv
import operator
from typing import Annotated, TypedDict, Union, Literal

import json
import pprint


from langchain_openai import AzureChatOpenAI

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, ToolMessage, AnyMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.agents import AgentAction, AgentFinish

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

VERSION = '0.7.1'
os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGCHAIN_PROJECT"] + f" - v. {VERSION}"


############################################
# Set up the model
llm_chatbot = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    streaming=True
)


################################################
# CREATE THE GRAPH MANUALLY

main_prompt = """
You are a helpful agent designed to help the user get the information they requested.

You collaborate with another agent that retrieves the information for you.

When a user asks you a question, you will forward the query to another agent. To the user, 
you answer "Your query is: " and repeat the user's query.

When you receive an answer from the other agent, repeat it word by word to the user. 

If the other agent answers "No information found", you MUST apologize to the user.
Then, you will create a well-formatted JSON request to be forwarded to the Business Analytics department. 

The request should be in the following json format:

{{
    'project': {{'id': 123}},
    'summary': USER'S QUERY',
    'description': summary of the user's query,
    'issuetype': {{'name': 'Report'}},
}}

You will tell the user they can use the JSON request above to make their request to the Business Analytics
department.
"""

# Create a chain with the main prompt
primary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", main_prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
chat_runnable = primary_prompt | llm_chatbot



#----------------------------------------
# Define nodes

class SimpleAgentState(MessagesState):
    """Extends the default MessagesState to add a current answer type 
    to allow us to properly route the messages"""
    response_type: str


def chatbot(state: SimpleAgentState):
    last_message = state['messages'][-1]
    current_response_type = state['response_type']

    # Update the current response type if needed
    if isinstance(last_message, HumanMessage):
        # This is a user query
        current_response_type = 'user_query'
    elif isinstance(last_message, AIMessage):
        # This is an agent's response
        current_response_type = 'agent_response'
    
    invoke_input = {'messages': state['messages'], 'response_type': current_response_type}
    response = chat_runnable.invoke(invoke_input)
    output = {'messages': [response], 'response_type': current_response_type}
    return output

def retriever(state: SimpleAgentState):
    # If this is a user query, drop the last agent message and run the 
    # chain on the remaining messages
    response = runnable_retriever.invoke(state["messages"])
    output = {'messages': [response], 'response_type': 'agent_response'}
    return output


def route_query(
    state: SimpleAgentState,
) -> Literal["retriever", "__end__"]:
    """
    Use in the conditional_edge to the info retriever if there is a query. 
    Otherwise, route to the end.
    """
    response_type = state.get('response_type')
    
    # if isinstance(state, list):
    #     messages = state
    #     #ai_message = state[-1]
    # elif isinstance(state, dict):
    #     messages = state.get("messages", [])
    #     #ai_message = messages[-1]
    # else:
    #     raise ValueError(f"No messages found in input state to tool_edge: {state}")
    

    if response_type == 'user_query':
        # Routing to the query retriever
        return 'query'

    # Otherwise, go back to the chatbot
    return "__end__"



def route_tools(
    state: SimpleAgentState,
) -> Literal["tools", "done"]:
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
    return "done"

retriever_tool_node = ToolNode(tools=retriever_tool_belt)

#----------------------------------------
# Build the graph, connecting the edges

# Start the graph
graph_builder = StateGraph(SimpleAgentState)

# Add the nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("retriever", retriever)
graph_builder.add_node("retriever_tools", retriever_tool_node)

# Add the edges
graph_builder.add_edge(START, "chatbot")

graph_builder.add_conditional_edges(
    "chatbot",
    route_query,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"query": "retriever", "__end__": "__end__"},
)

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
    {"tools": "retriever_tools", "done": "chatbot"},
)

# Any time a tool is called, we return to the retriever to decide the next step
graph_builder.add_edge("retriever_tools", "retriever")


# Add memory to the agent using a checkpointer
graph = graph_builder.compile(checkpointer=MemorySaver())


########################
# Visualize the graph

# graph.get_graph().print_ascii()
# png_graph = graph.get_graph().draw_mermaid_png(
#             draw_method=MermaidDrawMethod.API,
#         )

# graph_path = '/mnt/c/Users/mbrandao/Downloads/graph.png'
# #graph_path = 'graph.png'
# with open(graph_path, 'wb') as png_file:
#     png_file.write(png_graph)

