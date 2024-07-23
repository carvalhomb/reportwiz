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

VERSION = '1.0_rc1'
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


#################################################################################
# RUNNABLE CHAINS
# Create our runnable chains, depending on the prompt we want to pass forward

main_prompt = """
You are a helpful agent designed to help the user get the information they requested.

You collaborate with another agent that retrieves the information for you.

When a user asks you a question, you will forward the query to another agent. To the user, 
you answer "Your query is: " and repeat the user's query.

You will receive information from another agent with the results of their research
into the user's query. Your task is to repeat it word by word to the user. 
Do not summarize the other agent's answer. 

You MUST cite your source documents.
"""

# Create a chain with the main prompt
main_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system", main_prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
chat_runnable = main_prompt_template | llm_chatbot

# ----------------------------------------------------------------
# Create a second chain with the prompt that tells the chatbot
# to route the query to the ticket creation

ticketing_prompt = """
                You are a helpful agent who helps the user send requests to the Business Analytics department.
                You are called only when the system was unable to find the user's requested information.

                Your task is, first, to apologize to the user for not finding the information.
                Then, you will take the user's query and create a well-formatted JSON request.
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
ticketing_prompt_template  = ChatPromptTemplate.from_messages(
    [
        (
            "system", ticketing_prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

ticketing_runnable = ticketing_prompt_template | llm_chatbot

#################################################################################
# MANUALLY CREATE OUR GRAPH

#------------------------------------
# We need a custom state

class SimpleAgentState(MessagesState):
    """Extends the default MessagesState to add a current answer type 
    to allow us to properly route the messages"""
    response_type: str

#------------------------------------
# Defining our nodes

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

    # Return an update to the state with the latest response
    output = {'messages': [response], 'response_type': current_response_type}
    return output


def ticketing_bot(state: SimpleAgentState):
    #current_response_type = state.get('response_type')
    
    # We manually set response_type to no_answer to invoke the chain
    invoke_input = {'messages': state['messages'], 'response_type': 'no_answer'}

    response = ticketing_runnable.invoke(invoke_input)

    # After we get the response, we manually set response_type to "ticket_generated"
    output = {'messages': [response], 'response_type': 'ticket_generated'}
    return output



def retriever(state: SimpleAgentState):
    # Run a retrieval query on the conversation state
    response = runnable_retriever.invoke(state["messages"])
    current_response_type = state.get('response_type')

    output = {'messages': [response], 'response_type': current_response_type}
    return output

# For the retriever tool node we use the inbuilt ToolNode
retriever_tool_node = ToolNode(tools=retriever_tool_belt)

#------------------------------------
# Defining our routing functions

def route_query(
    state: SimpleAgentState,
) -> Literal["retriever", "__end__"]:
    """
    Use in the conditional_edge to the info retriever if there is a query. 
    Otherwise, route to the end.
    """
    response_type = state.get('response_type')

    if response_type == 'user_query':
        # Routing to the query retriever
        return 'query'

    # Otherwise, go to the end
    return "__end__"


def route_tools(
    state: SimpleAgentState,
) -> Literal["tools", "success", "no_answer"]:
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, we check if the retriever found the information
    requested. If yes, we route to the end. Otherwise, we send the request
    to the ticketing bot.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"

    # Check if we couldn't find an answer
    if 'no information found' in ai_message.content.lower():
        return "no_answer"

    return "success"


#----------------------------------------
# Build the graph and connect the edges

# Start the graph
graph_builder = StateGraph(SimpleAgentState)

# Add the nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("retriever", retriever)
graph_builder.add_node("retriever_tools", retriever_tool_node)
graph_builder.add_node("ticketing_bot", ticketing_bot)

# Add the edges
graph_builder.add_edge(START, "chatbot")


graph_builder.add_conditional_edges(
    "chatbot",
    route_query,
    {"query": "retriever", "__end__": "__end__"},
)

graph_builder.add_conditional_edges(
    "retriever",
    route_tools,
    {"tools": "retriever_tools", "success": "chatbot", "no_answer": "ticketing_bot"},
)

# Any time a tool is called, we return to the retriever to decide the next step
graph_builder.add_edge("retriever_tools", "retriever")

# The ticketing bot goes directly to the end
graph_builder.add_edge("ticketing_bot", END)

#----------------------------------------
# Compile!
# Also, we add memory to the agent using a checkpointer
graph = graph_builder.compile(checkpointer=MemorySaver())


########################
# Visualize the graph

graph.get_graph().print_ascii()
png_graph = graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )

graph_path = '/mnt/c/Users/mbrandao/Downloads/graph.png'
#graph_path = 'graph.png'
with open(graph_path, 'wb') as png_file:
    png_file.write(png_graph)

