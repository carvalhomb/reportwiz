import os
from uuid import uuid4
import dotenv
from datetime import datetime
import pprint

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

from langgraph.checkpoint import MemorySaver

from langchain.agents import tool
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.agent_toolkits import SQLDatabaseToolkit


from retrieval import pdf_retriever


dotenv.load_dotenv()

os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGCHAIN_PROJECT"] + f" - {uuid4().hex[0:8]}"



############################################
# Set up the model
llm = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    #streaming=True
)

##############################################
#SQL agent

db_path = 'data/databases/database.db'

db = SQLDatabase.from_uri(f"sqlite:///{db_path}?mode=ro", sample_rows_in_table_info=3)


toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()

pprint.pprint(tools)



############################################
# Define the tools

tool_belt = [
    #DuckDuckGoSearchRun(),
    #ArxivQueryRun(),
    #get_word_length,
    #check_weather
    pdf_retriever
] + tools


######################################
# Prompt setup
system_message = SystemMessage(
    content="""
You are a helpful and knowleageble agent designed to help the user get useful information about solar panels and weather.

You have access to a repository of existing PDF reports that have already been produced on this topic.

When a user asks you a question, FIRST you search for existing reports. If there are existing reports that answer to the user's question,
you use the report to provide the information.

IF, and ONLY IF, you cannot find an existing report, you will interact with a SQL database to get that information.

Given an input question, create a syntactically correct SQLite query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.                               
                               
""")

# Add memory to the agent

memory = MemorySaver()

graph = create_react_agent(llm, tools=tool_belt, checkpointer=memory, messages_modifier=system_message)


# # Testing

# #msg = "What is RAG in the context of Large Language Models? When did it break onto the scene?"
# msg = 'How many letters in the work "eduac"?'
# #msg="what is the weather in sf"


# inputs = {"messages": [("user", msg )]}
# for s in graph.stream(inputs, stream_mode="values"):
#     message = s["messages"][-1]
#     if isinstance(message, tuple):
#         print(message)
#     else:
#         message.pretty_print()


