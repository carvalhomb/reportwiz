import os
import dotenv

import json



from langchain_openai import AzureChatOpenAI
from typing import Annotated, Literal
from typing_extensions import TypedDict



from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, ToolMessage, AnyMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.checkpoint import MemorySaver

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit


from retrieval import pdf_retriever


dotenv.load_dotenv()

VERSION = '0.5'

#os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGCHAIN_PROJECT"] + f" - {uuid4().hex[0:8]}"
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



############################################
# Define the tools

tool_belt = [
    pdf_retriever
] + tools


######################################
# Prompt setup

# Get the table metadata
with open(metadata_path, 'r') as f:
    table_metadata = f.read()

prompt = f"""
You are a helpful and knowleageble agent designed to help the user get useful information about solar panels and weather in Croatia.

You have access to two data sources on this topic:

1) A repository of existing PDF reports that have already been produced on this topic. 

2) An SQLite database that contains the following information:

========

{table_metadata}

==========

YOUR TASK:

When a user asks you a question, FIRST you search for existing reports. If there are existing reports that answer to the user's question,
you use the report to provide the information.

IF, and ONLY IF, you cannot find an existing report, you will interact with the SQL database to get that information.

Given an input question, create a syntactically correct SQLite query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
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

If you can't find an answer in the reports repository or in the database, you should answer with: "I could not find the information
you requested in the repository or in the dabatase. I will create a request to the Business Analytics department"

FRANKO, CONTINUE FROM HERE :)
                               
"""

#system_message = SystemMessage(content=prompt)


# Add memory to the agent
memory = MemorySaver()

#############################################
# CREATE PRE-BUILT GRAPH
# graph = create_react_agent(llm,
#                            tools=tool_belt,
#                            checkpointer=memory,
#                            messages_modifier=system_message
#                            )
#

################################################
# CREATE THE GRAPH MANUALLY

class State(TypedDict):
    messages: Annotated[list, add_messages]

class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}



# Modification: tell the LLM which tools it can call
llm_with_tools = llm.bind_tools(tool_belt)

# Create a chain with the prompt
primary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "user", prompt
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

chat_runnable = primary_prompt | llm_with_tools



def chatbot(state: State):
    return {"messages": [chat_runnable.invoke(state["messages"])]}

def route_tools(
    state: State,
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



graph_builder = StateGraph(State)

graph_builder.add_node("chatbot", chatbot)


tool_node = BasicToolNode(tools=tool_belt)
graph_builder.add_node("tools", tool_node)


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
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile(checkpointer=memory)

#graph.get_graph().print_ascii()
