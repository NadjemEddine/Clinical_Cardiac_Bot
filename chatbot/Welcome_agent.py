import os
from langchain_core.prompts import ChatPromptTemplate

from IPython.display import Image, display
from pydantic import BaseModel, Field
from datetime import date, datetime
from langchain_core.runnables import Runnable, RunnableConfig


from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from langchain.messages import HumanMessage

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt.tool_node import tools_condition
from langchain_deepseek import ChatDeepSeek


from .Welcome_agent_tools import Check_static_clinical_data, Update_static_clinical_data
from .tools_chat import create_tool_node_with_fallback, handle_tool_error


class StaticClinicalData(BaseModel):
    diabetes: bool = Field(description="Does the patient have diabetes? (True/False)")
    hypertension: bool = Field(
        description="Does the patient have hypertension? (True/False)"
    )
    stroke: bool = Field(description="Has the patient had a stroke? (True/False)")
    kidney_disease: bool = Field(
        description="Does the patient have kidney disease? (True/False)"
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
            state = {**state, "user_info": patient_id}
            result = self.runnable.invoke(state)

            # Your existing retry logic
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not any(block.get("text") for block in result.content if isinstance(block, dict))
            ):
                messages = state["messages"] + [HumanMessage(content="Please provide a proper response.")]
                state = {**state, "messages": messages}
            else:
                break

        return {"messages": result}


def create_agent():
    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.5-flash-lite",
    #     api_key=os.getenv("GEMINI_API_KEY")
    # )
    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=1.3,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=os.getenv("DEEPSEEK_API_KEY"),

    )

    # llm = ChatOllama(
    #     model="qwen2.5:0.5b",
    #     temperature=0,
    #     request_timeout=300,
    #     base_url="http://localhost:11434",
    # )
    # llm = ChatOpenAI(
    #     temperature=0.7,
    #     model="mistralai/devstral-2512:free",
    #     api_key=os.getenv("OPENROUTER_API_KEY"),
    #     base_url="https://openrouter.ai/api/v1",
    # )
    

    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
'''You are a professional medical assistant agent responsible for collecting and updating a patient's static clinical information.  
You operate inside a LangGraph workflow and you MUST always use your available tools to retrieve and update the patient’s data.

You have access to the following tools:
- Check_static_clinical_data: retrieve all current static clinical attributes for the patient.
- Update_static_clinical_data: update any single clinical attribute for the patient with "yes" or "no".

You MUST ALWAYS:
1. Read the `patient_id` from the configuration parameter `<User>{user_info}</User>`.  
2. Use `Check_static_clinical_data` FIRST to know what information is missing.  
3. Ask the patient ONLY about attributes that are still missing.  
4. After every user answer, call `Update_static_clinical_data` with:
   - patient_id
   - field_name
   - value ("yes" or "no")
5. After updating, call `Check_static_clinical_data` again to check what is still missing.
6. Continue until all attributes are filled.

List of attributes to collect:
- diabetes
- hypertension
- smoke
- kidney_disease
- hypertension_medicales
- physical_activity
- astheme
- pulmonary_disease
- alcoholic
- walking_problem
- e_cigarette
- covid_19
- prevouis_stroke

When all attributes are complete say:
"All your clinical data are updated."

Be warm, empathetic, and human-like.  
Never speak in bullets or lists—use natural conversation.  
Never assume answers; ALWAYS ask the patient and then use the proper tool.
For every question you should wait for the patient's answer before proceeding.
dont go question looping. questions is about one or two attributes at a time.  
Never return empty tool calls.'''

                "\n\nCurrent user:\n<User>\n{user_info}\n</User>"
                "\nCurrent time: {time}.",
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now)

    part_1_tools = [
        Check_static_clinical_data,
        Update_static_clinical_data,
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
