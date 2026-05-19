import asyncio
import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .agent import create_agent
from langchain.messages import HumanMessage, AIMessage
from langchain_core.messages import ToolMessage

from .models import Conversation


from typing import Dict
from langchain_core.runnables import Runnable, RunnableConfig

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_name = None
        self.room_group_name = None
        self.agent = None
        self.patient_id = None
        self.state = {
            'messages': [],
        }
        self.agentName = "Daily_Agent"
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        print(f"WebSocket connected. Room name: {self.room_name}, Group name: {self.room_group_name}")

        # Initialize the agent
        self.agent = create_agent()
        print("Agent created successfully.")

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print("WebSocket connection accepted.")

        # Send a welcome message to the client
        welcome_message = "Welcome to ClinicalBot. Type `q` to quit. Let’s collect some health information. What can you tell me about your health history?"
        await self.send(text_data=json.dumps({"response": welcome_message, "tool":None}))
        print(f"Sent welcome message: {welcome_message}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        
        # --- Save in the database via sync_to_async ---
        await database_sync_to_async(Conversation.objects.create)(
            patient_id=self.patient_id,
            thread_id=self.room_name,
            state=self.state,
            agent=self.agentName,
        )
        
        print(f"WebSocket disconnected. Close code: {close_code}")

    async def receive(self, text_data):
        print(f"Received message from client: {text_data}")

        # Parse the incoming message
        try:
            data = json.loads(text_data)
            message = data.get("message", "")
            patient_id = data.get("patient_id", None)
            print(f"Parsed message: {message}, Patient ID: {patient_id}")
        except json.JSONDecodeError as e:
            error_message = f"Invalid JSON input: {str(e)}"
            await self.send(text_data=json.dumps({"error": error_message}))
            print(error_message)
            return

        if not patient_id:
            error_message = "Patient ID is required"
            await self.send(text_data=json.dumps({"error": error_message}))
            print(error_message)
            return

        # Prepare the state and config for the agent
        # state = {"messages": [HumanMessage(message)]}
        config = {
            "configurable": {
                # The patient_id is used in our clinical data tools to fetch the user's patient information
                "patient_id": patient_id,
                "websocket": self,
                # Checkpoints are accessed by thread_id
                "thread_id": self.room_name,
            }
        }
        print(f"Prepared state, Config: {config}")
        self.patient_id = patient_id
        try:
            print(f"Streaming agent response...")
            async for chunk in self.agent.astream(
                    {"messages": [message]}, config, stream_mode="values"
                ):
                text = ''
                tool_name = ''
                type = ''
                tool_call = ''

                # --- Normalize all chunk types ---
                # Convert AIMessage/HumanMessage directly to dict wrapper
                if isinstance(chunk, (HumanMessage, AIMessage, ToolMessage)):
                    chunk = {"messages": [chunk]}

                # Ignore anything that is not a dict
                if not isinstance(chunk, dict):
                    continue

                msgs = chunk.get("messages", [])
                if not msgs:
                    continue

                last = msgs[-1]

                # ---- CASE 1: ToolMessage ----
                # These must NEVER reach UI, only used internally
                if isinstance(last, ToolMessage):
                    type = "Tool Message"
                    text = last.content
                    tool_name = last.name
                    tool_call = ""
                    self.state['messages'].append({'type': type, 'content': text, 'tool_name': tool_name, 'tool_call': tool_call})
                    
                    # This is a tool result → skip sending to patient
                    continue

                # ---- CASE 2: Convert Human/AI message to dict ----
                if isinstance(last, (HumanMessage, AIMessage)):
                    if isinstance(last, HumanMessage):
                        type = "Human Message"
                        text = last.content
                        tool_name = ""
                    if isinstance(last, AIMessage):
                        type = "AI Message"
                        text = last.content
                        tool_name = ""
                    last = last.dict()

                # If still not dict → skip
                if not isinstance(last, dict):
                    continue

                # ---- Detect tool call (function_call) ----
                kwargs = last.get("additional_kwargs", {})
                if "function_call" in kwargs:
                    # LLM is calling a tool → do NOT show it to user
                    tool_call = kwargs["function_call"]["name"]
                    self.state['messages'].append({'type': type, 'content': text, 'tool_name': tool_name, 'tool_call': tool_call})

                    continue
                else:
                    tool_call = ""
                    self.state['messages'].append({'type': type, 'content': text, 'tool_name': tool_name, 'tool_call': tool_call})

                # ---- Detect tool result types ----
                if last.get("type") in ["tool", "tool_message", "tool_result"]:
                    continue

                # ---- Now extract only REAL user-facing content ----
                content = last.get("content")
                if not content or content.strip() == "":
                    continue

                # ---- Detect sender ----
                sender = "agent"
                if last.get("type", "").startswith("human"):
                    sender = "patient"

                # ---- Send clean text-only chunk to client ----
                await self.send(text_data=json.dumps({
                    "response": content,
                    "sender": sender,
                    "tool": None
                }))

        except Exception as e:
            error_detail = traceback.format_exc()   # This gives the FULL stack trace
            print("\n" + "="*60)
            print("FULL ERROR TRACEBACK:")
            print(error_detail)
            print("="*60 + "\n")
            
            error_message = f"Agent streaming failed: {str(e)}"
            await self.send(text_data=json.dumps({"error": error_message}))
            return
