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


from retrieval import pdf_retriever


dotenv.load_dotenv()

VERSION = '0.6'
os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGCHAIN_PROJECT"] + f" - v. {VERSION}"



############################################
# Set up the model
llm = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    streaming=True
)

##############################################
#SQL agent

db_path = 'data/databases/database.db'
metadata_path = 'data/databases/tables_metadata.md'

db = SQLDatabase.from_uri(f"sqlite:///{db_path}?mode=ro", sample_rows_in_table_info=3)

# Use the SQLDatabaseToolkit as described in
# https://python.langchain.com/v0.2/docs/tutorials/sql_qa/
# and https://api.python.langchain.com/en/latest/agent_toolkits/langchain_community.agent_toolkits.sql.toolkit.SQLDatabaseToolkit.html
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()



##########################
#Helpfulness checker tool


@tool
def check_helpfulness(input):
    """
    Check whether an answer is helpful or not, given a user's initial query.
    """
    initial_query = input["initial_query"]
    final_response = input["final_response"]


    helpfulness_prompt_template = """\
    Given an initial query and a final response, determine if the final response is helpful or not. 
    Please indicate helpfulness with a 'Y' and unhelpfulness as an 'N'.

    Initial Query:
    {initial_query}

    Final Response:
    {final_response}"""

    helpfulness_prompt_template = PromptTemplate.from_template(helpfulness_prompt_template)

    helpfulness_chain = helpfulness_prompt_template | llm | StrOutputParser()

    helpfulness_response = helpfulness_chain.invoke({"initial_query" : initial_query, "final_response" : final_response})

    if "Y" in helpfulness_response:
        print("Helpful!")
        return "Helpful"
    else:
        print("Not helpful!")
        return "Not helpful"

############################################
# Define the tools

tool_belt = [
    pdf_retriever,
    check_helpfulness
] + tools

tool_belt = [check_helpfulness]

######################################
# Prompt setup

# Get the table metadata
with open(metadata_path, 'r') as f:
    table_metadata = f.read()


json_format = """
{{
    'project': {{'id': 123}},
    'summary': USER'S QUERY',
    'description': summary of the user's query,
    'issuetype': {{'name': 'Report'}},
}}
"""

helpfulness_json = """
{{'initial_query': USER'S REQUEST,
'final_response': YOUR FINAL RESPONSE TO BE EVALUATED
}}
"""

prompt = f"""
You are a helpful and knowleageble agent designed to help the user get useful information 
about solar panels and weather in Croatia. When the user asks you for information that you
don't have access to, you help them generate a well-formatted ticket to be sent to the 
Business Analytics department.

You have access to two data sources:

1) A repository of existing PDF reports that have already been produced on this topic. 

2) An SQLite database that contains the following information:

========

{table_metadata}

==========

YOUR TASK:

When a user asks you a question, FIRST you search for existing reports. If there are existing 
reports that answer to the user's question, you use the report to provide the information.

IF, and ONLY IF, you cannot find an existing report, you will interact with the SQL database to get that information.

Given an input question, create a syntactically correct SQLite query to run, then look at 
the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit 
your query to at most 5 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it to ensure it is a valid SQLite query. 
If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.       

If you can't find an answer in the reports repository or in the database, DO NOT ANSWER! 
If the user asks you to generate any plots, DO NOT ANSWER! In those cases, you help them generate a
well-formatted ticket to the Business Analytics department.

Once you think you have searched all sources and have a final answer, you should use your helpfullness checker tool to
check whether the answer you have is helpful or not, given the user's query. Call the tool with the following JSON format:
{helpfulness_json}
 
If the tool indicates that your answer is not helpful,
you should apologize to the user for not finding the information they requested. Then,
you should create a well-formatted request ticket in the following JSON format:

{json_format}
 
Finally, tell the user they can use the formatted JSON request below to send a request to the 
Business Analytics department.
"""

prompt = f"""
You are a helpful agent.

After you generate a final response to the user, you MUST check whether your answer is helpful or not before sending it to the user.
Call the helpfulness checker tool with the following JSON format:
{helpfulness_json}

If the answer is not helpful, you should say "BUAAAAAA". If your answer is helpful, you should say "I'm the BEST!"
"""

# Add memory to the agent
memory = MemorySaver()

################################################
# CREATE THE GRAPH MANUALLY

# Create a chain with the main prompt and the llm bound with tools
primary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
chat_runnable = primary_prompt | llm.bind_tools(tool_belt)


# ### Ticket generation chain

# ticket_prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system", f"""
# "You are a helpful assistant who creates tickets for the Business Analytics department.
# Your task is to take the user's request and create a well-formatted request ticket.
#
# In addition to a response to the user, create a JSON request in the following format:
#
# {json_format}
#
# Tell the user that we are sorry that we could not find the information they requested. Also, tell them
# they can use the formatted JSON request below to send a request to the Business Analytics department.
#
# """
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#     ]
# )
# ticket_runnable = ticket_prompt | llm

#----------------------------------------
# Define nodes

def chatbot(state: MessagesState):
    return {"messages": [chat_runnable.invoke(state["messages"])]}

# def ticket_agent(state: MessagesState):
#     initial_query = state["messages"][0]
#     inputs = {"messages": [initial_query]}
#     return {"messages": [ticket_runnable.invoke(inputs)]}

# def dummy_node(state: MessagesState):
#   return


    

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




tool_node = ToolNode(tools=tool_belt)

#----------------------------------------
# Build the graph, connecting the edges

# Start the graph
graph_builder = StateGraph(MessagesState)

# Add the nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)
# graph_builder.add_node("passthrough", dummy_node)
# graph_builder.add_node("ticket_agent", ticket_agent)


# Add the edges
graph_builder.add_edge(START, "chatbot")

# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "__end__" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "tools", "__end__": "__end__"},
)

# graph_builder.add_conditional_edges(
#     "passthrough",
#     check_helpfulness,
#     {
#         "dispatch_ticket" : "ticket_agent",
#         "end" : END
#     }
# )

# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")

#graph_builder.add_edge("chatbot", END)


graph = graph_builder.compile(checkpointer=memory)




# graph.get_graph().print_ascii()
# png_graph = graph.get_graph().draw_mermaid_png(
#             draw_method=MermaidDrawMethod.API,
#         )
#
# #graph_path = '/mnt/c/Users/mbrandao/Downloads/graph.png'
# graph_path = 'graph.png'
# with open(graph_path, 'wb') as png_file:
#     png_file.write(png_graph)

#from langchain_core.messages import HumanMessage

# import uuid
# conversation_id = str(uuid.uuid4())
# config = {"configurable": {"thread_id": conversation_id}}

# inputs = {"messages" : [HumanMessage(content="What is the weather like in Brasilia, Brazil?")]}

# messages = graph.invoke(inputs, config=config,)