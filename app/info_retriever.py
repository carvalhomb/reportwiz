
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


from pdf_retriever import pdf_retriever


dotenv.load_dotenv()



##############################################
#SQL agent

db_path = 'data/databases/database.db'
metadata_path = 'data/databases/tables_metadata.md'

db = SQLDatabase.from_uri(f"sqlite:///{db_path}?mode=ro", sample_rows_in_table_info=3)

# Get the table metadata
with open(metadata_path, 'r') as f:
    table_metadata = f.read()



############################################
# Set up the model
llm_retriever = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    streaming=True
)

# Use the SQLDatabaseToolkit as described in
# https://python.langchain.com/v0.2/docs/tutorials/sql_qa/
# and https://api.python.langchain.com/en/latest/agent_toolkits/langchain_community.agent_toolkits.sql.toolkit.SQLDatabaseToolkit.html
toolkit = SQLDatabaseToolkit(db=db, llm=llm_retriever)
tools = toolkit.get_tools()

retriever_tool_belt = tools + [pdf_retriever]


prompt = f"""
You are a helpful agent designed to help the user get useful information 
about solar panels and weather in Croatia. You only provide information that you can
find in your data sources. You MUST ALWAYS cite your sources. 

When the user asks you for information that you don't have access to, you MUST answer with: 'No information found'.

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

If you can't find an answer in the reports repository or in the database, you MUST answer with: 'No information found'.
If the user asks you to generate any plots or reports, you MUST answer with: 'No information found'.

"""


prompt_retriever = ChatPromptTemplate.from_messages(
    [
        (
            "system", prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

runnable_retriever = prompt_retriever | llm_retriever.bind_tools(retriever_tool_belt)