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
    # to be able to use Langgraph's MemorySaver
    conversation_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conversation_id}}
    cl.user_session.set("config", config)

@cl.on_message
async def main(msg: cl.Message):
    """
    This function will be called every time a message is received from a session.
    """
    # msg is the user message,
    # agent_message is the agent's response.

    graph = cl.user_session.get("graph")
    config = cl.user_session.get("config")

    inputs = {"messages": [("user", msg.content)]}

    agent_message = cl.Message(content="")
    await agent_message.send()

    async for event in graph.astream_events(inputs, 
                                            version="v2", 
                                            config=config,
                                            ):
       
        kind = event["event"]
        event_name = event.get('name', '')

        if (kind == "on_chat_model_stream"):
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

        elif kind == 'on_chain_stream' and event_name in ('chatbot', 'ticket_agent'):
            print(event)
            chunk = event['data'].get('chunk', {})
            messages = chunk.get('messages', [])
            last_message = messages[-1]
            content = last_message.content
            reason = ''
            try:
                response_metadata = chunk.response_metadata
                reason = response_metadata.get('finish_reason', '')
            except Exception as e:
                pass

            if content:
                await agent_message.stream_token(content)
            if reason == 'stop':
                # Add a new line to avoid garbled output of formatted text
                await agent_message.stream_token(' \n')

                
    # Send empty message to stop the little ball from blinking
    await agent_message.send()
