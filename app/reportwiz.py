import os
import dotenv

import json
import pprint


from langchain_openai import AzureChatOpenAI
from typing import Annotated, Literal
from typing_extensions import TypedDict



from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, ToolMessage, AnyMessage, HumanMessage, AIMessage
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

# json_format = """
# {{
#     'project': {{'id': 123}},
#     'summary': USER'S QUERY',
#     'description': summary of the user's query,
#     'issuetype': {{'name': 'Report'}},
# }}
# """

json_schema = {
    "title": "response",
    "description": "Chatbot response",
    "type": "object",
    "properties": {
        "contents": {
            "type": "string",
            "description": "The model's response or the original user query",
        },
        "response_type": {
            "type": "string",
            "description": "whether final_response or user_query",
        },
    },
    "required": ["response_type"],
}

main_prompt = """
You are a helpful agent designed to help the user get the information they requested.

You collaborate with another agent that retrieves the information for you.

When a user asks you a question, you create a JSON response with response_type = user_query, 
which will be forwarded to another agent.

When you receive an answer, classify it as response_type = final_response and repeat it
word by word to the user. 
                               
"""



# continue_prompt = """
# However, if the other agent cannot find the information, you MUST apologize to the user.
# Then, you will create a well-formatted JSON request to be forwarded to the Business Analytics department. 

# The request should be in the following json format:

# {json_format}

# You will tell the user they can use the JSON request above to make their request to the Business Analytics
# department.
# """

# Create a chain with the main prompt
primary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", main_prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
chat_runnable = primary_prompt | llm_chatbot.with_structured_output(json_schema, method='json_mode', include_raw=True)



#----------------------------------------
# Define nodes

def chatbot(state: MessagesState):
    print('Im the chatbot')
    response = chat_runnable.invoke(state["messages"])
    print(response)
    print('...........................')
    response_type = response['parsed'].get('response_type', '')
    if response_type == 'user_query' or response_type == '':
        message = response['raw']
        message.content = response['parsed'].get('query', '')
        if message.content == '':
            message.content = response['parsed'].get('contents', '')
        if message.content == '':
            message.content = response['parsed'].get('user_query', '')
        if message.content == '':
            message.content = response['parsed'].get('content', '')
        response_type = 'user_query'
    elif response_type == 'final_response':
        message = response['raw']
        message.content = response['parsed'].get('contents', '')   
        if message.content == '':
            message.content = response['parsed'].get('content', '') 
    print(type(message))
    print(message)
    print('------------------------------?????-----------------')
    return {"messages": [message], "type": response_type}

def retriever(state: MessagesState):
    #print("I'm the retriever")
    response = runnable_retriever.invoke(state["messages"])
    return {"messages": [response]}


def route_query(
    state: MessagesState,
) -> Literal["retriever", "__end__"]:
    """
    Use in the conditional_edge to the info retriever if there is a query. 
    Otherwise, route to the end.
    """
    #print('QUERY ROUTING.........................')
    response_type = state.get('type', '')
    #print(f'response type is {response_type}')

    if isinstance(state, list):
        messages = state
        #ai_message = state[-1]
    elif isinstance(state, dict):
        messages = state.get("messages", [])
        #ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    

    if response_type == 'user_query':
        #print('ROUTING QUERY TO RETRIEVER!.........................')
        return 'query'

    #print('----------no query to route, returning to chatbot')
    return "__end__"



def route_tools(
    state: MessagesState,
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
graph_builder = StateGraph(MessagesState)

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



# import uuid
# conversation_id = str(uuid.uuid4())
# config = {"configurable": {"thread_id": conversation_id}}

# inputs = {"messages" : [HumanMessage(content="What is the weather like in Vukovar?")]}

# messages = graph.invoke(inputs, config=config,)
# print(messages)