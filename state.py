from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # conversation history
    customer_info: dict                       # collected lead data
    current_intent: str                       # pricing/objection/demo/escalate
    handoff_needed: bool                      # should we schedule human?