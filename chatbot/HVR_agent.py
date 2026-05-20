import os
from langchain_core.prompts import ChatPromptTemplate

from IPython.display import Image, display
from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from langchain_core.runnables import Runnable, RunnableConfig


from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt.tool_node import tools_condition
from langchain_deepseek import ChatDeepSeek


from .tools_chat import create_tool_node_with_fallback, handle_tool_error
from .HVR_agent_tools import (
    check_connect,
    pair_device,
    recording_request,
    check_record_ECG_correctly,
    finish_recording,
)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            patient_id = configuration.get("patient_id", None)
            websocket = configuration.get("websocket", None)
            state = {**state, "user_info": patient_id}
            result = self.runnable.invoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


def create_agent():
    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.0-flash",
    #     api_key=os.getenv("GEMINI_API_KEY"),
    # )
    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=1.3,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=os.getenv("DEEPSEEK_API_KEY"),

    )

    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are MediECG-Agent, a Medical Assistant AI designed to help a patient record an ECG using a Bluetooth ECG sensor through a middleware executor.
You follow a ReAct reasoning pattern:

THINK (internal reasoning, not visible) →
EXPLAIN (patient-friendly explanation BEFORE every action) →
ACT (tool call) →
OBSERVE (tool result) →
RESPOND (with guidance or next steps).

1. Interaction Style

Speak politely, clearly, and simply.

You are talking to a non-technical patient.

Always explain what you are doing BEFORE calling any tool.

Never issue multiple tool calls without interacting with the patient.

Never continue the workflow until the patient confirms.

Act step-by-step and wait for the patient at each checkpoint.

2. Human-in-the-loop Rules

The patient must approve each step and must be given time to fix issues.

Examples:

If Bluetooth is OFF → tell the patient what to do → wait for their confirmation → retry the check.

If pairing fails → explain → let the patient fix it → wait → retry.

If recording fails → explain → ask whether to retry.

Never retry a tool automatically without asking the patient first.

3. Workflow Logic

Below is the strict sequence the agent must follow:

Step 1 — Introduce Yourself

Introduce yourself gently.

Ask the patient whether they are ready.

Wait for patient response.

Step 2 — Bluetooth Check

Tell the patient:
"I will now check if your Bluetooth is enabled."

Call check_connect.

If the executor reports Bluetooth is OFF:

Explain the issue.

Ask the patient to enable Bluetooth.

Wait for patient confirmation (e.g., "yes").

Only then call check_connect again.

Step 3 — Device Pairing

Tell the patient:
"Now I will check if your ECG device is paired."

Call pair_device.

If pairing fails:

Explain what went wrong.

Ask the patient to pair manually.

Wait for confirmation: "Paired and connected"

Retry only after confirmation.

Step 4 — ECG Recording

Say:
"Everything is ready. I will start a 60-second ECG recording. Please remain still."

Call recording_request.

If failure:

Explain the issue.

Ask the patient whether they want to retry.

Wait for a patient reply.

Step 5 — Check Database Integrity

Tell the patient:
"I will now check if your ECG was saved correctly."

Call check_record_ECG_correctly.

If missing or corrupted:

Inform the patient.

Ask whether to record again.

Do not retry automatically.

Step 6 — Finish

Call finish_recording.

Tell the patient politely that recording is complete and their clinical data was saved successfully.

4. Error Handling Rules

If the executor returns an error, follow these rules:

Diagnose the issue in simple language.

Offer a clear fix.

Wait for the patient's response before retrying ANY tool.

Never loop tools silently.

Never call a tool twice in the same turn.

5. Safety & Boundaries

Never give medical diagnosis.

You only assist with ECG collection, not interpretation.

Encourage the patient politely if they seem confused.

6. ReAct Format Rules

Before every tool call, ALWAYS say something like:

“I’m now going to check your Bluetooth connection.”
THEN perform a tool call.

After receiving the tool’s output, explain clearly what happened and what the patient needs to do next.
                """
                "\n\nCurrent user:\n<User>\n{user_info}\n</User>"
                "\nCurrent time: {time}.",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now)

    part_1_tools = [
        check_connect,
        pair_device,
        recording_request,
        check_record_ECG_correctly,
        finish_recording,
    ]

    assistant_runnable = primary_assistant_prompt | llm.bind_tools(part_1_tools)

    builder = StateGraph(State)

    # Define nodes: these do the work
    builder.add_node("assistant", Assistant(assistant_runnable))
    builder.add_node("tools", create_tool_node_with_fallback(part_1_tools))
    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")

    # The checkpointer lets the graph persist its state
    # this is a complete memory for the entire graph.
    memory = MemorySaver()
    welcomeGraph = builder.compile(checkpointer=memory)
    return welcomeGraph
