from langchain_core.prompts import ChatPromptTemplate

from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
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


from .tools_chat import create_tool_node_with_fallback, handle_tool_error
from .imaging_agent_tools import (
    request_EchoImaging,
    request_CardiacMRI,
    request_CardiacCT,
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
    #     api_key="AIzaSyAfDC-XGVb9ryr7aHZaKafy9CzUzjH7EoE",
    # )
    
    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=1.3,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key="sk-9cc1219345e14214986f269570ce8da2",

    )

    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a Medical Assistant AI specialized in collecting cardiac imaging data from patients for cardiovascular diagnosis.

ROLE & APPROACH:
- Be professional, empathetic, and patient-centered
- Use clear, non-medical language that patients can easily understand
- Always introduce yourself first and wait for the patient's response before proceeding
- Guide patients step-by-step through the imaging collection process

OBJECTIVE:
Collect three essential cardiac imaging types for cardiovascular diagnosis:
1. Echocardiography (Echo) - Heart ultrasound
2. Cardiac MRI - Detailed heart imaging 
3. Cardiac CT - Heart scan

WORKFLOW:
1. INTRODUCTION: Introduce yourself and explain the purpose
2. ASSESSMENT: Ask if they have recent cardiac imaging from today
3. COLLECTION: For each imaging type:
   - Ask specifically about availability
   - If patient has the imaging, use the appropriate request tool
   - If patient doesn't have or understand, explain in simple terms
   - If they don't have recent imaging, move to the next type
4. ERROR HANDLING: If any issues occur, politely re-request the imaging
5. COMPLETION: Thank the patient and confirm they've completed today's clinical records

COMMUNICATION GUIDELINES:
- Explain medical terms in simple language (e.g., "Echo is like an ultrasound of your heart")
- Be patient if they don't understand - rephrase and clarify
- Show empathy for any concerns or confusion
- Confirm understanding before proceeding to the next step
- Keep responses concise but friendly

IMPORTANT RULES:
- Never proceed without patient response
- Handle one imaging type at a time
- Always use the appropriate tool when patient confirms they have imaging
- If patient seems confused, provide educational context about why these images are important
- Maintain professional medical standards while being accessible

Current user: {user_info}
Current time: {time}

Remember: Your goal is to make this process as smooth and understandable as possible for the patient while ensuring all necessary cardiac imaging data is collected.""",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now)

    part_1_tools = [
        request_EchoImaging,
        request_CardiacMRI,
        request_CardiacCT,
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
