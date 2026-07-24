import json
import os
import sqlite3
import traceback
from typing import Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import list_files_and_folders, read_file, delete_file, get_env_value
from context import SYSTEM_PROMPT
from dotenv import load_dotenv
from langgraph.types import Command
from openai import OpenAI, pydantic_function_tool
from db import Base, ChatHistory, get_async_db, get_db, engine
from sqlalchemy.orm import Session

Base.metadata.create_all(bind=engine)

load_dotenv()
# Initialize FastAPI App
app = FastAPI(title="AI Chat Service with Memory and Tools")

# Environment / Database Configuration
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


#----------------------------
# Tool Definition & classes
#----------------------------

class ListfilesArgs(BaseModel):
    directory_path: str = Field(description="directory path to list the files from")

class ReadFileArgs(BaseModel):
    file_path: str = Field(description="Path of the file which needs to be read")

class DeleteFileArgs(BaseModel):
    file_path: str = Field(description="Path of the file which needs to be deleted")

class GetEnvArgs(BaseModel):
    var_name: str = Field(description="name of the environment variable")

available_tools = {
    "list_files_and_folders": list_files_and_folders, "read_file": read_file, 
    "delete_file": delete_file, "get_env_value": get_env_value
}

custom_tools = [
    pydantic_function_tool(name="list_files_and_folders", model=ListfilesArgs),
    pydantic_function_tool(name="read_file", model=ReadFileArgs),
    pydantic_function_tool(name="delete_file", model=DeleteFileArgs),
    pydantic_function_tool(name="get_env_value", model=GetEnvArgs)
]

# ------------------------------------------------------------------
# 2. Define Request/Response Models
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: str
    message: str
    resume_interrupt: bool
    resume_decision: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tools_used: List[str]
    interrupt: bool
    interrupt_description: str
    interrupt_options: List[str]
    interrupt_args: Dict
    input_tokens: int
    output_tokens: int
    total_tokens: int
    est_input_tokens: float
    est_output_tokens: float
    est_total_tokens: float
    boiler_tokens: float
    boiler_percent: float

class ChatMessageItem(BaseModel):
    type: str  # e.g., 'human', 'ai', 'system', 'tool'
    content: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageItem]

class AgenticResponse(BaseModel):
    message: str = Field(description="A brief response to user query")
    tools_used: List[str] = Field(description="List of tools used for answering user queries")

# 1. Initialize the SQLite connection
# check_same_thread=False is safe because SqliteSaver uses internal locking
conn = sqlite3.connect("chat_history.db", check_same_thread=False)
# checkpointer = SqliteSaver(conn)

# # ------------------------------------------------------------------
# # 3. LangChain Agent Setup
# # ------------------------------------------------------------------
# # llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.0)
# llm = ChatOpenAI(model="gpt-5.4-mini", temperature=0.0)
# agent = create_agent(
#     model=llm,
#     tools=available_tools,
#     checkpointer=checkpointer,
#     system_prompt=SYSTEM_PROMPT,
#     middleware=[ 
#         HumanInTheLoopMiddleware(
#             interrupt_on={
#                 "list_files_and_folders": False,
#                 "read_file": False,
#                 "delete_file": {
#                     "allowed_decisions": ["approve", "reject"],
#                     "description": "File deletion requires approval"
#                 },
#                 "get_env_value": False,
#             }
#         )
#     ],
#     response_format=AgenticResponse  # <--- Forces agent to produce structured output
# )

#-------------------------------------------------------------
# Message Calling Loop
#-------------------------------------------------------------

def message_tool_call_loop(messages: List[Dict[str, str]], response_format) -> tuple[str, List[Dict[str, str]], int]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.parse(
    model="gpt-5.4-mini",
    store=False,
    messages=messages,
    tools=custom_tools,
    response_format=response_format
)
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    print(f"""

{response_message}

""")
    if tool_calls:
        messages.append(response_message)
        for tool_call in tool_calls:
            function_name = tool_call.function.name 
            function_args = json.loads(tool_call.function.arguments)
            if function_name in available_tools:
                print(f"Tool Name: {function_name}, Args: {function_args}")
                try:
                    tool_output = available_tools[function_name](**function_args)
                    if not tool_output:
                        tool_output = f"Tool: {function_name} produced no output"
                except Exception as e:
                    print(f"tool error: {e}")
                    tool_output = f"Error occurred: {e}, {traceback.format_exc()}"
                messages.append({ "tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": tool_output })
        return message_tool_call_loop(messages, response_format)
    else:
        messages.append(response_message)
        return response_message, messages, response.usage.total_tokens



# ------------------------------------------------------------------
# 4. API Endpoints
# ------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
        # if not OPENAI_API_KEY:
        #     raise HTTPException(
        #         status_code=500, 
        #         detail="OPENAI_API_KEY environment variable is not set."
        #     )

        # try:
        config = { "configurable": { "thread_id": request.session_id }}
        # Run the agent with context
        # if request.resume_interrupt:
        #     response = agent.invoke(
        #         Command(
        #             resume={"decisions": [{"type": request.resume_decision }]}
        #         ),
        #         config=config,
        #         version="v2"
        #     )
        # else:
        #     response = agent.invoke({
        #         "messages": [
        #             {
        #                 "role": "user", "content": request.message
        #             }
        #         ]
        #     },
        #     config=config,
        #     version="v2"
        #     )
        # state = agent.get_state(config)
        session = db.get(ChatHistory, request.session_id)
        est_input_tokens = 0
        est_output_tokens = 0
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        boiler_tokens = 0
        boiler_percent = 0
        if session:
            messages = session.messages 
            messages.append({ 'role': 'user', 'content': request.message })
        else:
            messages = [
                { 'role': 'system', 'content': SYSTEM_PROMPT },
                { 'role': 'user', 'content': request.message }
            ]
        message, messages, total_tokens = message_tool_call_loop(messages, AgenticResponse)
        # Save Chat History
        msgs = []
        for m in messages:
            print(type(m), m)
            if type(m) != dict:
                m = m.model_dump()
            msgs.append(m)
        if session:
            session.messages = msgs
            session.tokens_used = total_tokens
            db.commit()
        else:
            session = ChatHistory(session_id=request.session_id, messages=msgs, tokens_used=total_tokens)
            db.add(session)
            db.commit()
        # Input Token Estimation
        system_prompt_len = len(SYSTEM_PROMPT)
        user_prompt_list = [msg["content"] for msg in msgs if msg["role"] == "user" or msg["role"] == "tool"]
        user_prompt_len = len("".join(user_prompt_list))
        est_input_tokens = (system_prompt_len + user_prompt_len) / 4

        # Est output tokens
        ai_response_list = [msg["content"] for msg in msgs if msg["role"] == "ai"]
        ai_response_len = len("".join(ai_response_list))
        est_output_tokens = ai_response_len/4

        est_total_tokens = est_input_tokens + est_output_tokens
        # Token Calculation
        boiler_tokens = total_tokens - est_total_tokens      
        boiler_percent = (boiler_tokens/total_tokens) * 100  

        response_message = message
        interrupt = False
        interrupt_description = ""
        interrupt_options = []
        interrupt_args = {}
        tools_used = []
        if False:
            interrupt = True
            interrupt_description = response.interrupts[0].value["action_requests"][0]["description"]
            interrupt_args = response.interrupts[0].value["action_requests"][0]["args"]
            interrupt_options = response.interrupts[0].value['review_configs'][0]['allowed_decisions']
        else:
            agent_response: AgenticResponse = message.parsed
            response_message = agent_response.message
            tools_used = agent_response.tools_used
        return ChatResponse(
            session_id=request.session_id,
            response=response_message,
            tools_used=tools_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            est_input_tokens=est_input_tokens,
            est_output_tokens=est_output_tokens,
            est_total_tokens=est_total_tokens,
            boiler_tokens=boiler_tokens,
            boiler_percent=round(boiler_percent, 2),
            interrupt=interrupt,
            interrupt_description=interrupt_description,
            interrupt_options=interrupt_options,
            interrupt_args=interrupt_args
        )
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Retrieve all past messages for a specific session ID."""
    try:
        session = db.get(ChatHistory, session_id)
        if not session:
            return { "messages": [], "tokens_used": 0 }
        return { "messages": session.messages, "tokens_used": session.tokens_used }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/history/{session_id}")
def delete_chat(session_id: str, db: Session = Depends(get_db)):
    try:
        session = db.get(ChatHistory, session_id)
        if not session:
            return None 
        db.delete(session)
        db.commit()
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")