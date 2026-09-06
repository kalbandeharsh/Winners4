"""
EcoSphere - LangGraph Sales Agent with Tools
Enhanced version with RAG-powered responses and tool calling.
"""

import os
import sys
import json
from typing import TypedDict, Annotated, List, Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.rag import get_knowledge_base
from tools.product_lookup import get_product_lookup
from tools.calendar import get_scheduler
from .state import AgentState, create_initial_state

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.7, max_tokens=256)

# ---------------------------------------------------------------------------
# Knowledge Base & Tools
# ---------------------------------------------------------------------------
kb = get_knowledge_base()
product_lookup = get_product_lookup()
scheduler = get_scheduler()

# ---------------------------------------------------------------------------
# LangChain Tools
# ---------------------------------------------------------------------------

@tool
def search_products(query: str) -> str:
    """
    Search the product catalog for pricing and feature information.
    Use this when customers ask about products, plans, pricing, or features.
    
    Args:
        query: What to search for (e.g., "Enterprise pricing", "Pro plan features")
    
    Returns:
        Relevant product information from the catalog
    """
    results = kb.search(query, n_results=2)
    
    if not results:
        return "No matching products found. We offer Starter ($29/mo), Pro ($79/mo), and Enterprise ($199/mo) plans."
    
    response = "Here's what I found:\n"
    for i, result in enumerate(results):
        response += f"\n{i+1}. {result['text']}"
    
    return response


@tool
def get_pricing_summary() -> str:
    """
    Get a summary of all pricing plans.
    Use this when customers ask about pricing or want to compare plans.
    
    Returns:
        Formatted pricing summary with all plans
    """
    return kb.get_pricing_summary()


@tool
def schedule_meeting(
    customer_name: str,
    email: str,
    company: str = "",
    context: str = ""
) -> str:
    """
    Schedule a meeting with a human sales agent.
    Use this when customers want a demo, have complex needs, or request human assistance.
    
    Args:
        customer_name: Customer's full name
        email: Customer's email address
        company: Customer's company name (optional)
        context: Summary of the conversation and customer needs
    
    Returns:
        Meeting confirmation with details
    """
    meeting = scheduler.schedule_meeting(
        customer_name=customer_name,
        email=email,
        company=company,
        context=context
    )
    return scheduler.get_meeting_confirmation(meeting)


@tool
def get_competitor_comparison(competitor_name: str) -> str:
    """
    Get comparison information against a competitor.
    Use this when customers mention competitors or ask for comparisons.
    
    Args:
        competitor_name: Name of the competitor to compare against
    
    Returns:
        Professional comparison highlighting EcoSphere advantages
    """
    return kb.get_competitor_response(competitor_name)


# List of all tools
tools = [search_products, get_pricing_summary, schedule_meeting, get_competitor_comparison]

# ---------------------------------------------------------------------------
# System Prompts (Enhanced with RAG context)
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """You are a friendly, professional AI sales assistant for EcoSphere - a Real-Time Voice AI platform for sales teams.

Your goals:
1. Understand the customer's needs and pain points
2. Qualify the lead (budget, timeline, decision-maker)
3. Guide toward a clear next step (demo, trial, purchase)

IMPORTANT GUIDELINES:
- This is a VOICE conversation - keep responses SHORT (2-3 sentences max)
- Ask ONE question at a time
- Use the customer's name if you know it
- Be conversational and warm
- Use tools to get accurate product information - never make up prices
- If they want a demo or seem ready, schedule a meeting
- If they have objections, acknowledge and address them empathetically

You have access to these tools:
- search_products: Find product information and pricing
- get_pricing_summary: Get all pricing plans
- schedule_meeting: Book a demo with sales team
- get_competitor_comparison: Compare against competitors
"""

PRICING_PROMPT = """You are answering a pricing question. Use the search_products tool to get accurate, up-to-date pricing information.

Guidelines:
- Be transparent about pricing - no hidden fees
- Highlight value, not just cost
- If they need a custom quote, offer to schedule a call
- Keep responses short and voice-friendly
"""

OBJECTION_PROMPT = """You are handling a customer objection with empathy.

Common objections and responses:
- "Too expensive" → Focus on ROI. Ask what budget they're working with.
- "Already have a solution" → Ask what's working and what isn't. Position as complementary.
- "Need to think about it" → Ask what specific concerns remain.
- "Not the right time" → Ask about their timeline. Offer to follow up.
- "Need to talk to my boss" → Offer to prepare a summary for their manager.

Guidelines:
- Acknowledge their concern FIRST
- Never be pushy
- Ask clarifying questions
- Always offer a clear next step
"""

DEMO_PROMPT = """You are scheduling a demo or meeting.

Your job:
1. Confirm their interest
2. Collect: name, email, company (use schedule_meeting tool)
3. Confirm the details back to them

Be enthusiastic but professional. Use the schedule_meeting tool when you have enough info.
"""

# ---------------------------------------------------------------------------
# Tool-enhanced Agent Node
# ---------------------------------------------------------------------------

def agent_node(state: AgentState) -> AgentState:
    """
    Main agent node that uses tools to answer questions.
    """
    # Build messages with system prompt
    messages = [SystemMessage(content=BASE_SYSTEM_PROMPT)] + state["messages"]
    
    # Get last user message for context
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, str):
            last_user_msg = msg
            break
        elif hasattr(msg, "content") and isinstance(msg.content, str):
            last_user_msg = msg.content
            break
    
    # Add RAG context if available
    if last_user_msg:
        context = kb.format_for_context(last_user_msg, max_length=300)
        if context and context != "No relevant information found.":
            messages.append(SystemMessage(content=f"Relevant product context:\n{context}"))
    
    # Get response from LLM with tools
    try:
        response = llm.bind_tools(tools).invoke(messages)
    except Exception as e:
        # Fallback without tools if binding fails
        response = llm.invoke(messages)
    
    # Extract customer info if present
    customer_info = state["customer_info"].copy()
    
    # Check for tool calls in response
    if hasattr(response, "tool_calls") and response.tool_calls:
        # Store tool calls for execution
        return {
            **state,
            "messages": state["messages"] + [response],
            "_pending_tool_calls": response.tool_calls
        }
    
    return {
        **state,
        "messages": state["messages"] + [response],
    }


def tool_executor(state: AgentState) -> AgentState:
    """Execute pending tool calls and add results to state."""
    tool_calls = state.get("_pending_tool_calls", [])
    
    if not tool_calls:
        return state
    
    messages = state["messages"].copy()
    
    for tool_call in tool_calls:
        # Find and execute the tool
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Execute tool
        if tool_name == "search_products":
            result = search_products.invoke(tool_args)
        elif tool_name == "get_pricing_summary":
            result = get_pricing_summary.invoke(tool_args)
        elif tool_name == "schedule_meeting":
            result = schedule_meeting.invoke(tool_args)
            # Mark handoff needed after scheduling
            return {
                **state,
                "messages": messages + [ToolMessage(content=result, tool_call_id=tool_call["id"])],
                "handoff_needed": True,
                "handoff_reason": "Customer requested a demo/meeting."
            }
        elif tool_name == "get_competitor_comparison":
            result = get_competitor_comparison.invoke(tool_args)
        else:
            result = f"Unknown tool: {tool_name}"
        
        messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
    
    return {
        **state,
        "messages": messages,
        "_pending_tool_calls": []
    }


def should_continue(state: AgentState) -> str:
    """Determine if we should continue with tool calls or end."""
    if state.get("_pending_tool_calls"):
        return "tools"
    return END

# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_sales_graph():
    """
    Build the enhanced LangGraph sales conversation graph with tools.
    
    Flow:
        agent -> (if tool calls) -> tools -> agent -> END
        agent -> (if no tool calls) -> END
    """
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_executor)
    
    # Set entry point
    graph.set_entry_point("agent")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # Tools always go back to agent
    graph.add_edge("tools", "agent")
    
    return graph.compile()


# Create the graph instance
sales_graph = build_sales_graph()


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("="*60)
    print("EcoSphere Sales Agent (Enhanced with Tools)")
    print("="*60)
    
    # Create initial state
    state = create_initial_state()
    
    # Simulate conversation
    test_messages = [
        "Hi, I'm interested in your product",
        "How much does the Pro plan cost?",
        "That seems expensive compared to competitors",
        "Can I schedule a demo?"
    ]
    
    for msg in test_messages:
        print(f"\n👤 User: {msg}")
        
        # Add user message
        state["messages"] = state["messages"] + [HumanMessage(content=msg)]
        
        # Run through graph
        result = sales_graph.invoke(state)
        state = result
        
        # Get last AI response
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "content"):
            print(f"🤖 Agent: {last_msg.content}")
        
        # Check state
        print(f"   [Intent: {state['current_intent']}]")
        print(f"   [Handoff: {state['handoff_needed']}]")
        
        if state["conversation_complete"]:
            print("\n--- Conversation ended ---")
            break
    
    print("\n" + "="*60)
    print("Test complete!")
