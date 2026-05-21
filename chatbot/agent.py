import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
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

from .tools_chat import (
    Check_for_updates,
    create_tool_node_with_fallback,
    finish_collected,
    update_missing_clinical_data,
    handle_tool_error,
)

class ClinicalData(BaseModel):
    diabetes: bool = Field(description="Does the patient have diabetes? (True/False)")
    hypertension: bool = Field(description="Does the patient have hypertension? (True/False)")
    stroke: bool = Field(description="Has the patient had a stroke? (True/False)")
    kidney_disease: bool = Field(description="Does the patient have kidney disease? (True/False)")
    glucose_level: int = Field(description="What is the patient's glucose level? (in mg/dL)")
    systolic_bp: int = Field(description="What is the patient's systolic blood pressure? (in mmHg)")
    diastolic_bp: int = Field(description="What is the patient's diastolic blood pressure? (in mmHg)")
    
# Try using different models. The `pro` models perform the best, especially
# with tool-calling. The `flash` models are super fast, and are a good choice
# if you need to use the higher free-tier quota.
# Check out the features and quota differences here: https://ai.google.dev/pricing




class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]




class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            patient_id = configuration.get("patient_id", None)
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
    # llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))
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
            "You are Medical Assistant collecting daily clinical records from the patient. "
            "CRITICAL: Ask ONLY ONE question per message. Never list multiple questions in a single message. "
            "Wait for the patient to answer before asking the next question. "
            "Workflow:\n"
            "1. Use Check_for_updates to find missing fields.\n"
            "2. Ask about ONE missing field only.\n"
            "3. After patient answers, call update_missing_clinical_data.\n"
            "4. Repeat with one field at a time until all filled.\n"
            "5. When all done, call finish_collected.\n"
            "Available fields: weight (kg), height (cm), fasting (yes/no), chest_pain (yes/no), "
            "cholestrol_total (mg/dL), glucose_level (mg/dL), systolic_bp (mmHg), diastolic_bp (mmHg), "
            "removed_teeth (number)."
            "\n\nCurrent user:\n<User>\n{user_info}\n</User>"
            "\nCurrent time: {time}.",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now)
    
    part_1_tools = [
    Check_for_updates,
    update_missing_clinical_data,
    finish_collected,]
    
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
    part_1_graph = builder.compile(checkpointer=memory)
    return part_1_graph