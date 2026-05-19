import asyncio
import time
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
import json
from uuid import UUID
from django.utils import timezone


from .utils import response_events


@tool
async def request_EchoImaging(config: RunnableConfig) -> str:
    """
    this tool request the patient to uplaod his Echo Imaging attachment.

    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: "request sucessfully" if the request received by the patient, "Failed to request" otherwise.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        start_time = time.time()
        await websocket.send(
            json.dumps(
                {
                    "type": "call_js_function",
                    "function_name": "request_echo_imaging",
                    "args": [],
                    "sender": "tool",
                }
            )
        )

        return "request sucessfully"

    except Exception as e:

        return "request Failed"
    

#MRI IMAGing
@tool
async def request_CardiacMRI(config: RunnableConfig) -> str:
    """
    this tool request the patient to uplaod his Cardiac MRI Imaging attachment.

    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: "request sucessfully" if the request received by the patient, "Failed to request" otherwise.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        start_time = time.time()
        await websocket.send(
            json.dumps(
                {
                    "type": "call_js_function",
                    "function_name": "request_cardiac_mri",
                    "args": [],
                    "sender": "tool",
                }
            )
        )

        return "request sucessfully"

    except Exception as e:

        return "request Failed"
    
#Cardiac CT
@tool
async def request_CardiacCT(config: RunnableConfig) -> str:
    """
    this tool request the patient to uplaod his A cardiac computed tomography (CT) Imaging attachment.

    Args:
        config: Configuration dictionary containing the patient_id and WebSocket of the patient.

    Returns:
        str: "request sucessfully" if the request received by the patient, "Failed to request" otherwise.
    """
    configuration = config.get("configurable", {})
    websocket = configuration.get("websocket", None)

    if not websocket:
        return "No WebSocket connection provided."

    try:
        start_time = time.time()
        await websocket.send(
            json.dumps(
                {
                    "type": "call_js_function",
                    "function_name": "request_cardiac_ct",
                    "args": [],
                    "sender": "tool",
                }
            )
        )

        return "request sucessfully"

    except Exception as e:

        return "request Failed"