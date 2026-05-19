import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .imaging_agent import create_agent
from langchain.messages import HumanMessage, AIMessage
from typing import Dict
from langchain_core.runnables import Runnable, RunnableConfig
import datetime

import time


class ImagingConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_name = None
        self.room_group_name = None
        self.agent = None
        self.connection_time = None
        
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        print(
            f"WebSocket connected. Room name: {self.room_name}, Group name: {self.room_group_name}"
        )

        # Initialize the agent
        self.agent = create_agent()
        print("Agent created successfully.")

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        self.connection_time = datetime.datetime.now()

        print(f"WebSocket connection accepted. at {self.connection_time}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"WebSocket disconnected. Close code: {close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        print(f"Received raw message from client: {text_data}")  # Debug print

        # Parse the incoming message
        try:
            data = json.loads(text_data)
            print(f"Parsed data: {data}")  # Debug print
            message = data.get("message", "")
            patient_id = data.get("patient_id", None)
            print(f"Parsed message: {message}, Patient ID: {patient_id}")
        except json.JSONDecodeError as e:
            error_message = f"Invalid JSON input: {str(e)}"
            await self.send(text_data=json.dumps({"error": error_message}))
            print(error_message)
            return

        # Handle JavaScript function responses
        type_value = data.get("type", "")
        print(f"Type value (raw): '{type_value}'")
        print(f"Type value (repr): {repr(type_value)}")
        print(f"Type value length: {len(type_value)}")
        print(f"Type value stripped: '{type_value.strip()}'")
        print(f"Comparison: '{type_value.strip()}' == 'js_function_response' -> {type_value.strip() == 'js_function_response'}")
        
        
        
        if not patient_id:
            error_message = "Patient ID is required"
            await self.send(text_data=json.dumps({"error": error_message}))
            print(error_message)
            return

        # Check if this is a response from the client for the `check_connect` tool

        if data.get("type") == "call_js_function":
            # Handle the response for the `check_connect` tool
            result = data.get("result", "No result")
            print(f"Received response from client for `check_connect`: {result}")
            # You can store the result or process it further as needed
            return  # Do not pass this message to the agent

        # Prepare the state and config for the agent
        # state = {"messages": [HumanMessage(message)]}
        config = {
            "configurable": {
                # The patient_id is used in our clinical data tools to fetch the user's patient information
                "patient_id": patient_id,
                "websocket": self,  # Pass the WebSocket to the tool
                # Checkpoints are accessed by thread_id
                "thread_id": f"{patient_id}-{self.connection_time}",
            }
        }
        print(f"Prepared state, Config: {config}")

        try:

            # Stream the agent's response
            print("Streaming agent response...")
            async for chunk in self.agent.astream(
                {"messages": [message]}, config, stream_mode="values"
            ):
                #print(f"Chunk:){chunk}")
                tool = None
                sender = "agent"
                if isinstance(chunk, (HumanMessage, AIMessage)):
                    chunk = chunk.dict()  # Convert to dictionary
                    #print(f"ChunkDict:{chunk}")
                    response = chunk["messages"][-1].content
                    #print(f"Response :{response}")
                elif isinstance(chunk, dict):
                    chunk = {
                        k: v.dict() if isinstance(v, (HumanMessage, AIMessage)) else v
                        for k, v in chunk.items()
                    }
                    #print(f"Chunkelse:{chunk}")
                    response = chunk["messages"][-1].content
                    try:
                        tool = chunk["messages"][-1].additional_kwargs["function_call"][
                            "name"
                        ]
                    except:
                        pass
                    print(chunk["messages"][-1].pretty_print())

                # Send the chunk to the client
                await self.send(
                    text_data=json.dumps({"response": response, "tool": tool , 'sender': sender,})
                )
                print(f"Sent response chunk to client: {response}")
        except Exception as e:
            error_message = f"Agent streaming failed: {str(e)}"
            await self.send(text_data=json.dumps({"error": error_message}))
            print(error_message)
            return