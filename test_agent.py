"""
Quick test for the LangGraph sales agent graph (Enhanced).
Tests objection sub-routing, slot extraction, and persistence.
Run: python3 test_agent.py
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file

from agent.graph import sales_graph, checkpointer
from agent.state import create_initial_state, classify_objection_sub_type
from langchain_core.messages import HumanMessage


def test_objection_classification():
    """Test objection sub-type classification."""
    print("\n🔍 Objection Classification Tests:")
    print("-" * 40)

    cases = [
        ("This is too expensive for us", "price"),
        ("I don't trust AI with our data", "trust"),
        ("We're already using Twilio for this", "competitor"),
        ("Now is not the right time", "timing"),
        ("I need to check with my manager", "authority"),
        ("I'm not sure about this", "general"),
    ]

    for text, expected in cases:
        result = classify_objection_sub_type(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{text[:40]}...' → {result} (expected: {expected})")


def test_graph():
    """Test the full graph with enhanced state."""
    print("\n" + "=" * 60)
    print("EcoSphere Sales Agent — Enhanced Graph Test")
    print("=" * 60)

    state = create_initial_state()

    # Simulate a rich conversation
    test_messages = [
        "Hi, I'm interested in your product",
        "My name is John and I work at Acme Corp",
        "We have about 200 users who need AI calling",
        "How much does the Pro plan cost?",
        "That seems too expensive compared to Twilio",
        "I don't really trust AI for sales calls",
        "Can I schedule a demo?",
    ]

    config = {"configurable": {"thread_id": "test-session-001"}}

    for msg in test_messages:
        print(f"\n👤 User: {msg}")

        # Add user message to state
        state["messages"] = state["messages"] + [HumanMessage(content=msg)]

        # Run through graph with checkpointer
        result = sales_graph.invoke(state, config=config)
        state = result

        # Get the last AI response
        last_msg = state["messages"][-1]
        ai_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        print(f"🤖 Agent: {ai_response}")
        print(f"   [Intent: {state['current_intent']}]")
        print(f"   [Turn: {state['turn_count']}]")
        print(f"   [Handoff: {state['handoff_needed']}]")
        print(f"   [Outcome: {state['outcome']}]")
        print(f"   [User Count: {state.get('user_count')}]")
        print(f"   [Competitor: {state.get('competitor_mentioned')}]")
        print(f"   [Pricing Tier: {state.get('pricing_tier_discussed')}]")
        if state.get("objections"):
            print(f"   [Objections: {len(state['objections'])} — "
                  f"{', '.join(o['sub_type'] for o in state['objections'])}]")

        if state["conversation_complete"]:
            print("\n--- Conversation ended (handoff) ---")
            break

    # Verify persistence: load state from checkpointer
    print("\n" + "=" * 60)
    print("💾 Persistence Test")
    print("=" * 60)
    snapshot = checkpointer.get(config)
    if snapshot and snapshot.get("values"):
        print("  ✅ State saved to SqliteSaver — survives restart")
        saved = snapshot["values"]
        print(f"  Session turns: {saved.get('turn_count')}")
        print(f"  Objections recorded: {len(saved.get('objections', []))}")
    else:
        print("  ❌ State NOT found in checkpointer")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_objection_classification()
    test_graph()
