import os
import sqlite3
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
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

load_dotenv()
# Initialize FastAPI App
app = FastAPI(title="AI Chat Service with Memory and Tools")

# Environment / Database Configuration
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


available_tools = [list_files_and_folders, read_file, delete_file, get_env_value]

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
checkpointer = SqliteSaver(conn)

# ------------------------------------------------------------------
# 3. LangChain Agent Setup
# ------------------------------------------------------------------
# llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.0)
llm = ChatOpenAI(model="gpt-5.4-mini", temperature=0.0)
agent = create_agent(
    model=llm,
    tools=available_tools,
    checkpointer=checkpointer,
    system_prompt=SYSTEM_PROMPT,
    middleware=[ 
        HumanInTheLoopMiddleware(
            interrupt_on={
                "list_files_and_folders": False,
                "read_file": False,
                "delete_file": {
                    "allowed_decisions": ["approve", "reject"],
                    "description": "File deletion requires approval"
                },
                "get_env_value": False,
            }
        )
    ],
    response_format=AgenticResponse  # <--- Forces agent to produce structured output
)


# ------------------------------------------------------------------
# 4. API Endpoints
# ------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY environment variable is not set."
        )

    try:
        config = { "configurable": { "thread_id": request.session_id }}
        # Run the agent with context
        if request.resume_interrupt:
            response = agent.invoke(
                Command(
                    resume={"decisions": [{"type": request.resume_decision }]}
                ),
                config=config,
                version="v2"
            )
        else:
            response = agent.invoke({
                "messages": [
                    {
                        "role": "user", "content": request.message
                    }
                ]
            },
            config=config,
            version="v2"
            )
        state = agent.get_state(config)
        est_input_tokens = 0
        est_output_tokens = 0
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        boiler_tokens = 0
        boiler_percent = 0
        if state and state.values:
            msgs = state.values.get("messages", [])
            # Input Token Estimation
            system_prompt_len = len(SYSTEM_PROMPT)
            user_prompt_list = [msg.content for msg in msgs if msg.type == "human" or msg.type == "tool"]
            user_prompt_len = len("".join(user_prompt_list))
            est_input_tokens = (system_prompt_len + user_prompt_len) / 4
            # Output Token Estimation
            ai_response_list = [msg.content for msg in msgs if msg.type == "ai"]
            ai_response_len = len("".join(ai_response_list))
            est_output_tokens = ai_response_len/4
        est_total_tokens = est_input_tokens + est_output_tokens
        response_metadata = response["messages"][-1].response_metadata
        if "token_usage" in response_metadata:
            usage_metadata = response_metadata["token_usage"]
            total_tokens = usage_metadata["total_tokens"]
            boiler_tokens = total_tokens - est_total_tokens      
            boiler_percent = (boiler_tokens/total_tokens) * 100  
            input_tokens = usage_metadata["prompt_tokens"]
            output_tokens = usage_metadata["completion_tokens"]
        response_message = ""
        interrupt = False
        interrupt_description = ""
        interrupt_options = []
        interrupt_args = {}
        tools_used = []
        if response.interrupts:
            interrupt = True
            interrupt_description = response.interrupts[0].value["action_requests"][0]["description"]
            interrupt_args = response.interrupts[0].value["action_requests"][0]["args"]
            interrupt_options = response.interrupts[0].value['review_configs'][0]['allowed_decisions']
        else:
            agent_response: AgenticResponse = response["structured_response"]
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
def get_chat_history(session_id: str):
    """Retrieve all past messages for a specific session ID."""
    try:
        config = { "configurable": { "thread_id": session_id }}
        state = agent.get_state(config)
        if not state or not state.values:
            return HTTPException(status_code=404, detail=f"Session not found for ID: {session_id}")
        messages = state.values.get("messages", [])
            
        return { "messages": messages }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/history/{session_id}")
def delete_chat(session_id: str):
    try:
        # Re-use your global sqlite connection or open a transaction
        cur = conn.cursor()
        
        # SQLite checkpointer tables created by LangGraph
        cur.execute("DELETE FROM checkpoints WHERE thread_id = ?", (session_id,))
        cur.execute("DELETE FROM writes WHERE thread_id = ?", (session_id,))
        
        conn.commit()
        return {"message": "Chat history deleted successfully !!"}    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")