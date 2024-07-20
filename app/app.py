import uuid

import chainlit as cl

from reportwiz import graph


# @cl.set_starters
# async def set_starters():
#     return [
#         cl.Starter(
#             label="Temperatures in Zagreb",
#             message="What is the average temperature in Zagreb during the Summer?",
#             icon="/public/thermometer.svg",
#             ),

#         cl.Starter(
#             label="Solar panel production in Spring",
#             message="What is the average solar panel production in the spring?",
#             icon="/public/weather.svg",
#             ),
#         cl.Starter(
#             label="Best months for solar panel",
#             message="In which months is the solar panel production highest?",
#             icon="/public/sunny.svg",
#             ),
#         ]


@cl.on_chat_start
async def start_chat():
    
    cl.user_session.set("graph", graph)

    # Save the list in the session to store the message history
    cl.user_session.set("inputs", {"messages": []})

    # Create a thread id and pass it as configuration
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

    graph = cl.user_session.get("graph")
    config = cl.user_session.get("config")

    inputs = {"messages": [("user", msg.content)]}

    agent_message = cl.Message(content="")
    await agent_message.send()

    async for event in graph.astream_events(inputs, 
                                            version="v2", 
                                            config=config,
                                            #callbacks=[cl.LangchainCallbackHandler(stream_final_answer=True)]
                                            ):
        kind = event["event"]        
        #tags = event.get("tags", [])
        #event_name = event.get('name', '')        

        if kind == "on_chat_model_stream":
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
                
    # Send empty message to stop the little ball from blinking
    await agent_message.send()