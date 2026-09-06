"""
EcoSphere - FastAPI Server (Enhanced)
Wraps the LangGraph sales agent as an OpenAI-compatible endpoint.
Agora ConvoAI Engine connects to this server via CustomLLM.
Now with: persistent checkpointer, Slack escalation, session API.
"""

import os
import json
import asyncio
import time
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import httpx
from agora_token_builder import RtcTokenBuilder

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph import sales_graph, checkpointer
from agent.state import create_initial_state
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="EcoSphere LangGraph Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response models (OpenAI Chat Completions format)
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "ecosphere-sales-agent"
    messages: List[Message]
    stream: bool = True
    temperature: float = 0.7
    max_tokens: int = 256
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None

# ---------------------------------------------------------------------------
# Session management with checkpointer
# ---------------------------------------------------------------------------

# In-memory session index (maps session_id -> thread_id for checkpointer)
session_index: Dict[str, str] = {}

def get_or_create_thread(session_id: str) -> str:
    """Get existing thread_id for a session, or create a new one."""
    if session_id not in session_index:
        session_index[session_id] = f"session-{session_id}"
    return session_index[session_id]

def get_session_id(messages: List[Message]) -> str:
    """Extract or generate a stable session ID from messages.
    Uses only the first user message content as a stable key, so the same
    conversation always maps to the same session across turns.
    """
    for m in messages:
        if m.role == "user":
            # Use content hash for stable ID across growing message lists
            return str(abs(hash(m.content)))
    # Fallback: hash everything
    return str(abs(hash(str([(m.role, m.content[:50]) for m in messages[:3]]))))

# ---------------------------------------------------------------------------
# Slack escalation
# ---------------------------------------------------------------------------

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

async def send_slack_escalation(session_id: str, state: dict):
    """Send escalation to Slack with full conversation context."""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URL not set — skipping Slack escalation")
        return

    # Build conversation transcript
    transcript_lines = []
    for msg in state.get("messages", []):
        if hasattr(msg, "content"):
            role = "Customer" if isinstance(msg, HumanMessage) else "Agent"
            transcript_lines.append(f"**{role}**: {msg.content}")
    transcript = "\n".join(transcript_lines)

    customer = state.get("customer_info", {})
    objections = state.get("objections", [])

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 EcoSphere — Conversation Escalated"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Session:*\n{session_id}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"},
                    {"type": "mrkdwn", "text": f"*Customer:*\n{customer.get('name') or 'Unknown'}"},
                    {"type": "mrkdwn", "text": f"*Company:*\n{customer.get('company') or 'Unknown'}"},
                    {"type": "mrkdwn", "text": f"*Email:*\n{customer.get('email') or 'Not provided'}"},
                    {"type": "mrkdwn", "text": f"*Outcome:*\n{state.get('outcome', 'unknown')}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Reason:*\n{state.get('handoff_reason', 'Not specified')}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Objections ({len(objections)}):*\n" +
                    "\n".join(f"• [{o['sub_type']}] {o['text'][:80]}" for o in objections) if objections else "None"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Transcript:*\n```\n{transcript[:2500]}\n```"}
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"✅ Slack escalation sent for session {session_id}")
            else:
                print(f"❌ Slack escalation failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"❌ Slack escalation error: {e}")

# ---------------------------------------------------------------------------
# Main endpoint: OpenAI-compatible Chat Completions
# ---------------------------------------------------------------------------

@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    Agora ConvoAI Engine calls this to get agent responses.
    Uses SqliteSaver checkpointer for persistent session memory.
    """
    session_id = get_session_id(request.messages)
    thread_id = get_or_create_thread(session_id)

    # Get the last user message
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        return JSONResponse(
            status_code=400,
            content={"error": "No user message found"}
        )

    # Load existing state from checkpointer, or create fresh
    config = {"configurable": {"thread_id": thread_id}}

    # Check if we have existing state
    existing_state = None
    try:
        snapshot = checkpointer.get(config)
        if snapshot:
            vals = snapshot.get("values") or snapshot.get("channel_values")
            if vals:
                existing_state = vals
    except Exception:
        pass

    if existing_state is None:
        existing_state = create_initial_state()

    # Add user message to state
    state = {**existing_state}
    state["messages"] = state["messages"] + [HumanMessage(content=user_message)]

    # Run through LangGraph with checkpointer for persistence
    try:
        result = sales_graph.invoke(state, config=config)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Agent error: {str(e)}"}
        )

    # Get the AI response
    ai_response = result["messages"][-1].content if result["messages"] else "I'm sorry, I couldn't process that."

    # If handoff needed, fire Slack escalation asynchronously
    if result.get("handoff_needed") and not result.get("conversation_complete"):
        asyncio.create_task(send_slack_escalation(session_id, result))

    # Stream the response in OpenAI format
    if request.stream:
        return StreamingResponse(
            stream_response(ai_response, request.model),
            media_type="text/event-stream"
        )
    else:
        return {
            "id": f"chatcmpl-{session_id}",
            "object": "chat.completion",
            "created": 1234567890,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ai_response},
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }


async def stream_response(content: str, model: str):
    """Stream a response in OpenAI SSE format."""
    chunk_size = 20
    for i in range(0, len(content), chunk_size):
        chunk = content[i:i + chunk_size]
        data = {
            "id": "chatcmpl-stream",
            "object": "chat.completion.chunk",
            "created": 1234567890,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": chunk},
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.02)

    final_data = {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "created": 1234567890,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    yield f"data: {json.dumps(final_data)}\n\n"
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Session / conversation management endpoints
# ---------------------------------------------------------------------------

@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    print(f"🔍 /sessions called — session_index has {len(session_index)} entries: {list(session_index.keys())}")
    sessions = []
    for session_id, thread_id in session_index.items():
        try:
            snapshot = checkpointer.get({"configurable": {"thread_id": thread_id}})
            if snapshot:
                val = snapshot.get("values") or snapshot.get("channel_values")
            else:
                val = None
            if val:
                sessions.append({
                    "session_id": session_id,
                    "thread_id": thread_id,
                    "turn_count": val.get("turn_count", 0),
                    "current_intent": val.get("current_intent", "general"),
                    "outcome": val.get("outcome", "in_progress"),
                    "handoff_needed": val.get("handoff_needed", False),
                    "customer_name": val.get("customer_info", {}).get("name"),
                    "objections_count": len(val.get("objections", [])),
                })
            else:
                sessions.append({"session_id": session_id, "thread_id": thread_id, "status": "no-data"})
        except Exception as e:
            sessions.append({"session_id": session_id, "thread_id": thread_id, "status": "error", "error": str(e)})
    return {"sessions": sessions, "total": len(sessions)}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get detailed info about a specific session."""
    thread_id = session_index.get(session_id)
    if not thread_id:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    try:
        snapshot = checkpointer.get({"configurable": {"thread_id": thread_id}})
        val = None
        if snapshot:
            val = snapshot.get("values") or snapshot.get("channel_values")
        if val:
            # Serialize messages for API response
            messages = []
            for msg in val.get("messages", []):
                if hasattr(msg, "content"):
                    messages.append({
                        "role": "customer" if isinstance(msg, HumanMessage) else "agent",
                        "content": msg.content,
                    })
            return {
                "session_id": session_id,
                "thread_id": thread_id,
                "customer_info": val.get("customer_info"),
                "current_intent": val.get("current_intent"),
                "outcome": val.get("outcome"),
                "handoff_needed": val.get("handoff_needed"),
                "handoff_reason": val.get("handoff_reason"),
                "turn_count": val.get("turn_count"),
                "user_count": val.get("user_count"),
                "pricing_tier_discussed": val.get("pricing_tier_discussed"),
                "competitor_mentioned": val.get("competitor_mentioned"),
                "objections": val.get("objections", []),
                "messages": messages,
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return JSONResponse(status_code=404, content={"error": "Session data not found"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent": "ecosphere-sales-agent",
        "checkpointer": "sqlite",
        "slack_configured": bool(SLACK_WEBHOOK_URL),
        "active_sessions": len(session_index),
    }


@app.get("/")
async def root():
    return {
        "name": "EcoSphere LangGraph Server",
        "description": "OpenAI-compatible endpoint for Agora ConvoAI",
        "endpoints": {
            "chat": "/chat/completions",
            "health": "/health",
            "token": "/token?channel=CHANNEL_NAME",
            "sessions": "/sessions",
        }
    }


# ---------------------------------------------------------------------------
# Agora Token generation
# ---------------------------------------------------------------------------

AGORA_APP_ID = os.getenv("AGORA_APP_ID", "66d8b08dbc7f47aa8abeed25ee9b02f4")
AGORA_CERT = os.getenv("AGORA_APP_CERTIFICATE", "1e3fbbb8edf549adb224117bb3e87290")

@app.get("/token")
async def get_token(channel: str, uid: int = 0):
    """Generate an RTC token for a channel."""
    now = int(time.time())
    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID, AGORA_CERT, channel, uid,
        1, now + 3600
    )
    return {"token": token, "appId": AGORA_APP_ID, "channel": channel, "uid": uid}


# ---------------------------------------------------------------------------
# Run the server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting EcoSphere LangGraph Server...")
    print("📡 Endpoint: http://localhost:8000/chat/completions")
    print("🔌 Connect Agora Custom LLM to this URL")
    print("💾 Checkpointer: SqliteSaver (ecosphere.db)")
    if SLACK_WEBHOOK_URL:
        print("🔔 Slack escalation: ENABLED")
    else:
        print("🔕 Slack escalation: DISABLED (set SLACK_WEBHOOK_URL in .env)")
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ---------------------------------------------------------------------------
# Ping endpoint for latency measurement
# ---------------------------------------------------------------------------

@app.get("/ping")
async def ping():
    """Simple ping endpoint for measuring server latency."""
    return {"timestamp": time.time(), "status": "pong"}
