import asyncio
import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation
from .HVR_agent import create_agent
from langchain.messages import HumanMessage, AIMessage
from langchain_core.messages import ToolMessage
import datetime




class HVRChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_name = None
        self.room_group_name = None
        self.agent = None
        self.connection_time = None
        self.patient_id = None
        self.state = {
            'messages': [],
        }
        self.agentName = "electrod_IoT_Agent"
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
        # --- Save in the database via sync_to_async ---
        await database_sync_to_async(Conversation.objects.create)(
            patient_id=self.patient_id,
            thread_id=self.room_name,
            state=self.state,
            agent=self.agentName,
        )
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
            return  # Do not pass this message to the agentviews

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
    
        
