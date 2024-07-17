import os
from uuid import uuid4
import dotenv

from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain.agents import tool
from langgraph.prebuilt import ToolExecutor
from langchain_openai import AzureChatOpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

from langgraph.prebuilt import ToolInvocation
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
    response = len(word)+5
    return response


tool_belt = [
    DuckDuckGoSearchRun(),
    ArxivQueryRun(),
    get_word_length
]



tool_executor = ToolExecutor(tool_belt)
tools = [convert_to_openai_function(t) for t in tool_belt]

############################################
# Set up the model

#model = ChatOpenAI(model="gpt-4o", streaming=True)
model = AzureChatOpenAI(
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
    api_version="2024-05-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

model.bind_tools(tools)

# Prompt setup

system_message = SystemMessage(content="You are a not very knowleadgeable assistant. You are bad at calculating lengths of words. Use the tools you have available whenever possible.")



###########################################
# Build our graph

# Agent state
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Node "call model"
def call_model(state):
    messages = state["messages"]
    
    # Inject our system prompt
    messages_with_prompt = [system_message] + messages
    print(messages_with_prompt)

    response = model.invoke(messages_with_prompt)
    return {"messages" : [response]}

# Node "call tool"
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

    return {"messages" : [function_message]}


# Conditional function
def should_continue(state):
    last_message = state["messages"][-1]

    if "function_call" not in last_message.additional_kwargs:
        return "end"

    return "continue"







workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool)
workflow.set_entry_point("agent")



workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue" : "action",
        "end" : END
    }
)

workflow.add_edge("action", "agent")

app = workflow.compile()

# Vizualize the graph
#app.get_graph().print_ascii()

#####################################################


# Helper formatting function
def print_messages(messages):
    next_is_tool = False
    initial_query = True
    for message in messages["messages"]:
        if "function_call" in message.additional_kwargs:
            print()
            print(f'Tool Call - Name: {message.additional_kwargs["function_call"]["name"]} + Query: {message.additional_kwargs["function_call"]["arguments"]}')
            next_is_tool = True
            continue
        if next_is_tool:
            print(f"Tool Response: {message.content}")
            next_is_tool = False
            continue
        if initial_query:
            print(f"Initial Query: {message.content}")
            print()
            initial_query = False
            continue
    print()
    print(f"Agent Response: {message.content}")





# Testing

#msg = "What is RAG in the context of Large Language Models? When did it break onto the scene?"
msg = 'How many letters in the work "eduac"?'
inputs = {"messages" : [HumanMessage(content=msg)]}

messages = app.invoke(inputs)

print_messages(messages)


