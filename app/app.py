import uuid
import pprint

import chainlit as cl

from reportwiz import graph



@cl.on_chat_start
async def start_chat():
    
    cl.user_session.set("graph", graph)

    # Save the list in the session to store the message history
    cl.user_session.set("inputs", {"messages": []})

    # Create a thread id and pass it as configuration
    #config = {"metadata": {"conversation_id": str(uuid.uuid4())}}
    conversation_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conversation_id}}
    cl.user_session.set("config", config)

@cl.on_message
async def main(msg: cl.Message):
    """
    This function will be called every time a message is received from a session.
    """

    # msg is the user message,
    # agent_message is the agents.


    #graph: Runnable = cl.user_session.get("graph")
    graph = cl.user_session.get("graph")
    config = cl.user_session.get("config")

    inputs = {"messages": [("user", msg.content)]}

    agent_message = cl.Message(content="")
    await agent_message.send()

    # events = []
    # async for event in graph.astream_events(inputs, version="v2", config=config):
    #     events.append(event)

    # print(events)
    async for event in graph.astream_events(inputs, version="v2", config=config):
        kind = event["event"]        
        tags = event.get("tags", [])
        event_name = event.get('name', '')
        #print(f'{kind}--- tags: {tags} --- name: {event_name}')

        if kind == "on_chain_start":
            if (event["name"] == "agent"):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
                #print(f"Starting agent: {event['name']} with input: {event['data'].get('input')}")
                pass

        elif kind == "on_chain_end":
            if (event["name"] == "agent"):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
                #print()
                #print("--")
                #print(f"Done agent: {event['name']} with output: {event['data'].get('output')['output']}")
                #pass
                #messages = event["data"].get('output', {}).get('messages', [])
                #print(messages)
                #last_message = messages[-1]
                # agent_message.content = last_message.content
                # await agent_message.send()
                pass


        elif kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            response_metadata = event["data"]["chunk"].response_metadata
            
            if content:
                # Empty content in the context of OpenAI means
                # that the model is asking for a tool to be invoked.
                # So we only print non-empty content
                await agent_message.stream_token(content)

            if response_metadata.get('finish_reason', '') == 'stop':
                # Add a new line to avoid garbled output of formatted text
                await agent_message.stream_token(' \n')
                

        elif kind == "on_chain_stream":
            # print('Chain stream')
            # print(event)
            # print(f'event_name: {event_name}')
            # if event_name=='agent':
            #     content = event["data"].get("chunk")
            #     if content:
            #         await agent_message.stream_token(content)
            pass


        elif kind == "on_tool_start":
            #print("--")
            #print(f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}")
            pass

        elif kind == "on_tool_end":
            #print(f"Done tool: {event['name']}")
            #print(f"Tool output was: {event['data'].get('output')}")
            #print("--")
            pass
        else:
            #print(f"Non-accounted for kind of event: {kind}")
            pass


    # Send empty message to stop the little ball from blinking
    await agent_message.send()