"""
EcoSphere - LangGraph Sales Conversation Graph (Enhanced)
Routes conversations dynamically based on customer intent.
Includes objection sub-routing, slot extraction, and SqliteSaver checkpointer.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import re
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from .state import (
    AgentState, create_initial_state, add_objection,
    classify_objection_sub_type, update_customer_info,
)

# ---------------------------------------------------------------------------
# Mock LLM for testing without API keys
# ---------------------------------------------------------------------------

class MockChatLLM(BaseChatModel):
    """Mock LLM that returns canned intent-aware responses for testing."""
    model_name: str = "mock-llm"
    temperature: float = 0.7
    max_tokens: int = 256

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "mock-chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # Determine intent from the LAST user message (not system prompts)
        intent = "general"
        for msg in reversed(messages):
            if not (hasattr(msg, "content") and isinstance(msg.content, str)):
                continue
            content = msg.content.lower()
            # Check if this is a user message (not system/assistant)
            role = getattr(msg, "type", "")
            if role in ("system", "ai", "assistant"):
                continue
            if "price" in content or "cost" in content or "$79" in content or "how much" in content:
                intent = "pricing"
            elif "expensive" in content or "too much" in content or "price" in content:
                intent = "objection_price"
            elif "trust" in content or "reliable" in content or "security" in content:
                intent = "objection_trust"
            elif "competitor" in content or "alternative" in content or "vs" in content:
                intent = "competitor"
            elif "demo" in content or "schedule" in content or "meeting" in content:
                intent = "demo"
            elif "handoff" in content or "transfer" in content or "human" in content:
                intent = "handoff"
            break  # Only check the last user message

        responses = {
            "pricing": AIMessage(content="The Pro plan is $79/month with 1000 calls, advanced analytics, priority support, and API access. It's our most popular plan. Would you like to know about any specific features?"),
            "objection_price": AIMessage(content="I understand the budget concern. At $79/month for 1000 calls, that's under 8 cents per AI-powered sales interaction. We also offer a 14-day free trial so you can test the ROI before committing. What's your current spend on sales calls?"),
            "objection_trust": AIMessage(content="That's a fair concern. EcoSphere uses enterprise-grade security with SLA guarantees, and our RAG-grounded answers prevent hallucination. We have case studies from teams like yours. Would a live demo help build confidence?"),
            "competitor": AIMessage(content="Great question. Unlike raw telephony providers, EcoSphere adds the AI brain on top — handling the entire conversation with real-time interruption handling and persistent memory. What features matter most to your team?"),
            "demo": AIMessage(content="I'd love to set that up for you! I'll need your name, email, and company to schedule a demo. When works best for you?"),
            "general": AIMessage(content="Thanks for your interest! I'd love to learn more about your needs. What's the main challenge you're looking to solve with AI-powered sales calls?"),
            "handoff": AIMessage(content="I understand. Let me connect you with one of our specialists who can help you further. Just a moment while I set that up for you."),
        }
        return ChatResult(generations=[ChatGeneration(message=responses.get(intent, responses["general"]))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    @property
    def _identifying_params(self):
        return {"model_name": self.model_name}


# ---------------------------------------------------------------------------
# LLM (used by every node that needs to generate a response)
# ---------------------------------------------------------------------------
USE_MOCK = os.getenv("MOCK_LLM", "false").lower() in ("1", "true", "yes")

if USE_MOCK:
    print("🧪 Using Mock LLM (set MOCK_LLM=false for real LLM)")
    llm = MockChatLLM()
else:
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.7, max_tokens=256)

# ---------------------------------------------------------------------------
# System prompts per node
# ---------------------------------------------------------------------------
PRICING_PROMPT = """You are a knowledgeable sales agent at EcoSphere.
Answer pricing questions accurately using the product catalog below.

Product Catalog:
- Starter Plan: $29/month - 100 calls, basic analytics, email support
- Pro Plan: $79/month - 1000 calls, advanced analytics, priority support, API access
- Enterprise Plan: $199/month - Unlimited calls, custom analytics, dedicated support, SLA, custom integrations

Guidelines:
- Be transparent about pricing — no hidden fees.
- Highlight value, not just cost.
- If they need a custom quote, offer to schedule a call with the sales team.
- Keep responses short and conversational (voice-friendly)."""

OBJECTION_PRICE_PROMPT = """You are handling a customer's PRICE objection.
They think EcoSphere is too expensive. Address this by:
- Focusing on ROI and value (e.g., "At $79/mo for 1000 calls, that's under 8 cents per AI-powered sales interaction")
- Mentioning the 14-day free trial so they can try before committing
- Asking about their current spend on sales calls to show the comparison
Keep responses SHORT and conversational (voice call)."""

OBJECTION_TRUST_PROMPT = """You are handling a customer's TRUST objection.
They're worried about reliability, security, or whether your product actually works. Address this by:
- Mentioning enterprise-grade security and SLA guarantees
- Highlighting that RAG-grounded answers prevent hallucination
- Offering case studies or a live demo to build confidence
Keep responses SHORT and conversational (voice call)."""

OBJECTION_COMPETITOR_PROMPT = """You are handling a customer who's comparing you to a competitor.
They already have a solution or are considering alternatives. Address this by:
- Never badmouthing the competitor
- Asking what's working and what isn't with their current solution
- Positioning EcoSphere as complementary or a clear upgrade
- Highlighting unique strengths: real-time voice AI, interruption handling, persistent memory
Keep responses SHORT and conversational (voice call)."""

OBJECTION_TIMING_PROMPT = """You are handling a customer's TIMING objection.
They say it's not the right time. Address this by:
- Asking about their timeline and what would make it the right time
- Offering to send a summary email for later review
- Scheduling a follow-up call at a better time
Keep responses SHORT and conversational (voice call)."""

OBJECTION_AUTHORITY_PROMPT = """You are handling a customer's AUTHORITY objection.
They need to check with their manager or team. Address this by:
- Offering to prepare a one-page summary they can share
- Asking if they'd like to loop in their manager for a quick call
- Offering to schedule a demo that includes the decision-maker
Keep responses SHORT and conversational (voice call)."""

OBJECTION_GENERAL_PROMPT = """You are handling a customer objection with empathy.
The customer has raised a concern. Handle it gracefully.

Guidelines:
- Acknowledge their concern FIRST
- Never be pushy
- Ask clarifying questions to understand the real objection
- Always offer a clear next step
Keep responses SHORT and conversational (voice call)."""

DEMO_PROMPT = """You are a friendly sales agent scheduling a product demo.
The customer wants to see the product or schedule a meeting.

Your job:
1. Confirm their interest
2. Collect: name, email, company, preferred time
3. Let them know a human agent will reach out to confirm

Guidelines:
- Be enthusiastic but professional.
- Confirm the details back to them.
- Keep the conversation flowing naturally.
- If they give an email/name, acknowledge and save it."""

COMPETITOR_PROMPT = """You are a confident sales agent differentiating from competitors.
The customer mentioned a competitor or asked for a comparison.

Your approach:
- Never badmouth competitors — stay professional.
- Highlight EcoSphere's unique strengths:
  * Real-time voice AI with natural interruption handling
  * Stateful conversation memory (remembers the whole call)
  * RAG-grounded answers (no hallucination)
  * Easy integration with existing tools
- Ask what features matter most to them.

Guidelines:
- Be factual, not emotional.
- Turn the comparison into a discovery question.
- Keep responses short and conversational."""

GENERAL_PROMPT = """You are a friendly, professional AI sales assistant for EcoSphere.
You conduct natural sales conversations — qualify leads, understand needs, and guide toward a solution.

Your goals:
1. Understand the customer's needs and pain points
2. Qualify the lead (budget, timeline, decision-maker)
3. Guide the conversation toward a clear next step (demo, trial, purchase)

Guidelines:
- Be conversational and warm — this is a voice call, not a chat.
- Keep responses SHORT (2-3 sentences max).
- Ask one question at a time.
- Use the customer's name if you know it.
- If they seem ready to buy, offer to schedule a demo.
- If they seem unsure, address their concerns before pushing forward."""

# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def classify_intent(state: AgentState) -> AgentState:
    """Classify the user's intent from their latest message."""
    if not state["messages"]:
        return {**state, "current_intent": "general"}

    last_message = state["messages"][-1]
    if isinstance(last_message, str):
        user_text = last_message
    elif hasattr(last_message, "content"):
        user_text = last_message.content
    else:
        user_text = str(last_message)

    user_lower = user_text.lower()

    # Simple keyword-based classification (fast, no LLM call)
    pricing_keywords = ["price", "cost", "how much", "pricing", "plan", "expensive", "cheap", "budget", "afford", "rate"]
    objection_keywords = ["but", "however", "concern", "worried", "problem", "issue", "don't think", "not sure", "hesitant"]
    demo_keywords = ["demo", "meeting", "schedule", "call", "talk to someone", "human", "agent", "trial", "try"]
    competitor_keywords = ["competitor", "alternative", "vs", "compared", "already using", "switch", "other tool"]

    if any(kw in user_lower for kw in pricing_keywords):
        intent = "pricing"
    elif any(kw in user_lower for kw in competitor_keywords):
        intent = "competitor"
    elif any(kw in user_lower for kw in demo_keywords):
        intent = "demo"
    elif any(kw in user_lower for kw in objection_keywords):
        intent = "objection"
    else:
        intent = "general"

    # ---- Slot extraction: pull user_count, competitor_mentioned, pricing_tier from text ----
    updated_state = {**state, "current_intent": intent, "turn_count": state["turn_count"] + 1}

    # Extract user count (e.g., "we have 200 users", "team of 50")
    count_match = re.search(r'(\d+)\s*(?:users?|seats?|people|team of|team size)', user_lower)
    if count_match:
        updated_state["user_count"] = int(count_match.group(1))

    # Extract competitor mentioned
    for kw in competitor_keywords:
        if kw in user_lower:
            # Try to extract competitor name after the keyword
            match = re.search(rf'{kw}\s+(\w[\w\s]{{0,30}})', user_lower)
            if match:
                updated_state["competitor_mentioned"] = match.group(1).strip()

    # Extract pricing tier discussed
    if "enterprise" in user_lower:
        updated_state["pricing_tier_discussed"] = "enterprise"
    elif "pro" in user_lower:
        updated_state["pricing_tier_discussed"] = "pro"
    elif "starter" in user_lower:
        updated_state["pricing_tier_discussed"] = "starter"

    # Extract customer info (name, email, company)
    customer_info = state["customer_info"].copy()
    if "@" in user_text and not customer_info.get("email"):
        emails = re.findall(r'[\w.-]+@[\w.-]+\.\w+', user_text)
        if emails:
            customer_info["email"] = emails[-1]
    if "my name is" in user_lower or "i'm " in user_lower:
        name_match = re.search(r"(?:my name is|i'm|i am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", user_text)
        if name_match:
            customer_info["name"] = name_match.group(1)
    if "company" in user_lower or "work at" in user_lower:
        company_match = re.search(r"(?:company|work at|from)\s+([A-Z][\w\s]{1,30})", user_text)
        if company_match:
            customer_info["company"] = company_match.group(1).strip()
    if any(kw in user_lower for kw in ["budget", "spend", "allocate"]):
        budget_match = re.search(r'\$?([\d,]+)', user_text)
        if budget_match:
            customer_info["budget"] = budget_match.group(1)
    if any(kw in user_lower for kw in ["timeline", "by when", "deadline", "quarter"]):
        customer_info["timeline"] = user_text[:100]

    updated_state["customer_info"] = customer_info
    return updated_state


def route_intent(state: AgentState) -> str:
    """Route to the appropriate handler based on classified intent."""
    if state["handoff_needed"]:
        return "handoff"

    intent = state["current_intent"]
    return intent  # keys in the edges map match intent names


def handle_pricing(state: AgentState) -> AgentState:
    """Handle pricing questions using product catalog context."""
    messages = [
        SystemMessage(content=PRICING_PROMPT),
    ] + state["messages"]

    response = llm.invoke(messages)
    return {
        **state,
        "messages": state["messages"] + [response],
    }


def handle_objection(state: AgentState) -> AgentState:
    """
    Handle customer objections with sub-type classification.
    Routes to specialized prompts based on objection type.
    """
    # Get the user's objection text
    last_msg = state["messages"][-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Classify objection sub-type
    sub_type = classify_objection_sub_type(user_text)

    # Select the right prompt based on sub-type
    prompt_map = {
        "price": OBJECTION_PRICE_PROMPT,
        "trust": OBJECTION_TRUST_PROMPT,
        "competitor": OBJECTION_COMPETITOR_PROMPT,
        "timing": OBJECTION_TIMING_PROMPT,
        "authority": OBJECTION_AUTHORITY_PROMPT,
    }
    prompt = prompt_map.get(sub_type, OBJECTION_GENERAL_PROMPT)

    messages = [SystemMessage(content=prompt)] + state["messages"]
    response = llm.invoke(messages)

    # Record the objection
    objections = add_objection(state, user_text, sub_type)

    # After 3+ unique objections, suggest human handoff
    unique_types = set(o["sub_type"] for o in objections)
    handoff = len(objections) >= 3 or len(unique_types) >= 2

    return {
        **state,
        "messages": state["messages"] + [response],
        "objections": objections,
        "handoff_needed": handoff,
        "handoff_reason": (
            f"Customer raised {len(objections)} objections across {len(unique_types)} categories — "
            f"human agent recommended."
        ) if handoff else state["handoff_reason"],
    }


def handle_demo(state: AgentState) -> AgentState:
    """Handle demo/meeting scheduling requests."""
    messages = [
        SystemMessage(content=DEMO_PROMPT),
    ] + state["messages"]

    response = llm.invoke(messages)

    # Update outcome
    return {
        **state,
        "messages": state["messages"] + [response],
        "outcome": "demo_scheduled",
        "handoff_needed": True,
        "handoff_reason": "Customer requested a demo/meeting.",
    }


def handle_competitor(state: AgentState) -> AgentState:
    """Handle competitor comparisons."""
    messages = [
        SystemMessage(content=COMPETITOR_PROMPT),
    ] + state["messages"]

    response = llm.invoke(messages)
    return {
        **state,
        "messages": state["messages"] + [response],
    }


def handle_general(state: AgentState) -> AgentState:
    """Handle general conversation and lead qualification."""
    messages = [
        SystemMessage(content=GENERAL_PROMPT),
    ] + state["messages"]

    response = llm.invoke(messages)
    return {
        **state,
        "messages": state["messages"] + [response],
    }


def handle_handoff(state: AgentState) -> AgentState:
    """Generate a handoff message when transferring to a human agent."""
    handoff_msg = AIMessage(
        content=(
            f"I understand. Let me connect you with one of our specialists "
            f"who can help you further. {state['handoff_reason']} "
            f"Just a moment while I set that up for you."
        )
    )
    return {
        **state,
        "messages": state["messages"] + [handoff_msg],
        "conversation_complete": True,
        "outcome": "escalated",
    }


# ---------------------------------------------------------------------------
# Graph builder with SqliteSaver checkpointer
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecosphere.db")

# Initialize checkpointer with thread-safe SQLite connection
import sqlite3 as _sqlite3
_conn = _sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(_conn)
checkpointer.setup()


def build_sales_graph() -> StateGraph:
    """
    Build and compile the LangGraph sales conversation graph.

    Flow:
        classify_intent -> route -> [handler] -> classify_intent (loop)
        If handoff_needed -> handoff -> END

    Uses SqliteSaver for persistent session memory across restarts.
    """
    graph = StateGraph(AgentState)

    # --- Add nodes ---
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("handle_pricing", handle_pricing)
    graph.add_node("handle_objection", handle_objection)
    graph.add_node("handle_demo", handle_demo)
    graph.add_node("handle_competitor", handle_competitor)
    graph.add_node("handle_general", handle_general)
    graph.add_node("handle_handoff", handle_handoff)

    # --- Entry point ---
    graph.set_entry_point("classify_intent")

    # --- Conditional routing from classify_intent ---
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "pricing": "handle_pricing",
            "objection": "handle_objection",
            "demo": "handle_demo",
            "competitor": "handle_competitor",
            "general": "handle_general",
            "handoff": "handle_handoff",
        },
    )

    # --- Every handler ends the turn (single-pass per message) ---
    for node in ["handle_pricing", "handle_objection", "handle_competitor", "handle_general"]:
        graph.add_edge(node, END)

    # --- Handoff also ends the conversation ---
    graph.add_edge("handle_handoff", END)

    # --- Compile with checkpointer for persistent memory ---
    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Convenience: create a ready-to-use graph instance
# ---------------------------------------------------------------------------
sales_graph = build_sales_graph()
