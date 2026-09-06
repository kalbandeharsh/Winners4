"""
EcoSphere - Agent State Definition (Enhanced)
Defines the state that flows through the LangGraph graph during a sales conversation.
Includes rich slot tracking, objection history, and outcome fields.
"""

from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph.message import add_messages


class CustomerInfo(TypedDict):
    """Information collected about the customer during the call."""
    name: Optional[str]
    email: Optional[str]
    company: Optional[str]
    role: Optional[str]
    budget: Optional[str]
    timeline: Optional[str]
    pain_points: List[str]


class ObjectionRecord(TypedDict):
    """A single objection raised during the conversation."""
    text: str                        # what the customer said
    sub_type: str                    # price | trust | competitor | timing | authority | general
    resolved: bool                   # did we address it?


class AgentState(TypedDict):
    """
    Main state for the LangGraph sales agent.

    This state is maintained across the entire conversation and updated
    by each node in the graph.
    """
    # Conversation history - automatically accumulated by add_messages
    messages: Annotated[list, add_messages]

    # Customer qualification data collected during the call
    customer_info: CustomerInfo

    # ---- Richer session slots (from previous chat discussion) ----

    # How many users/seats the customer needs
    user_count: Optional[int]

    # Which pricing tier has been discussed so far
    pricing_tier_discussed: Optional[str]

    # Which competitor was mentioned (if any)
    competitor_mentioned: Optional[str]

    # Objection history with sub-classification
    objections: List[ObjectionRecord]

    # Overall conversation outcome
    # Options: "in_progress", "qualified", "demo_scheduled", "escalated", "lost", "converted"
    outcome: str

    # ---- Routing / handoff fields ----

    # Current classified intent from the last user message
    current_intent: str

    # Whether the conversation should be handed off to a human agent
    handoff_needed: bool

    # Reason for handoff (if applicable)
    handoff_reason: Optional[str]

    # Whether the conversation has reached a natural conclusion
    conversation_complete: bool

    # Track how many turns have occurred (for escalation logic)
    turn_count: int


def create_initial_state() -> AgentState:
    """Create a fresh initial state for a new conversation."""
    return AgentState(
        messages=[],
        customer_info=CustomerInfo(
            name=None,
            email=None,
            company=None,
            role=None,
            budget=None,
            timeline=None,
            pain_points=[],
        ),
        user_count=None,
        pricing_tier_discussed=None,
        competitor_mentioned=None,
        objections=[],
        outcome="in_progress",
        current_intent="general",
        handoff_needed=False,
        handoff_reason=None,
        conversation_complete=False,
        turn_count=0,
    )


def update_customer_info(state: AgentState, field: str, value) -> CustomerInfo:
    """Helper to update customer info without replacing the whole dict."""
    updated = state["customer_info"].copy()
    if field == "pain_points":
        if isinstance(value, str):
            updated["pain_points"] = updated["pain_points"] + [value]
        else:
            updated["pain_points"] = updated["pain_points"] + value
    else:
        updated[field] = value
    return updated


def add_objection(state: AgentState, text: str, sub_type: str = "general") -> List[ObjectionRecord]:
    """Add an objection record to the state."""
    record = ObjectionRecord(text=text, sub_type=sub_type, resolved=False)
    return state["objections"] + [record]


def classify_objection_sub_type(user_text: str) -> str:
    """Classify an objection into a sub-type based on keywords."""
    text = user_text.lower()

    price_kw = ["expensive", "cost", "price", "afford", "budget", "cheap", "worth", "overpriced", "too much"]
    trust_kw = ["trust", "reliable", "proven", "security", "safe", "risk", "guarantee", "warranty"]
    competitor_kw = ["competitor", "already have", "already using", "using", "we use", "switch", "alternative", "other tool", "vs", "compared"]
    timing_kw = ["not the right time", "later", "next quarter", "busy", "rush", "not ready"]
    authority_kw = ["talk to my boss", "manager", "decision maker", "approve", "sign off", "team lead"]

    if any(kw in text for kw in price_kw):
        return "price"
    if any(kw in text for kw in trust_kw):
        return "trust"
    if any(kw in text for kw in competitor_kw):
        return "competitor"
    if any(kw in text for kw in timing_kw):
        return "timing"
    if any(kw in text for kw in authority_kw):
        return "authority"
    return "general"
