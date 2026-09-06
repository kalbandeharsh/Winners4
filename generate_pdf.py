#!/usr/bin/env python3
"""
EcoSphere - Winners4 Hackathon Project Document
Generates a comprehensive PDF for team sharing
"""

from fpdf import FPDF
import os

class EcoSpherePDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, 'EcoSphere - Winners4 | Hackathon Project Document', 0, 1, 'C')
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(233, 69, 96)
        self.cell(0, 12, title, 0, 1)
        self.set_draw_color(233, 69, 96)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def sub_title(self, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(15, 52, 96)
        self.cell(0, 10, title, 0, 1)
        self.ln(2)

    def sub_sub_title(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(83, 52, 131)
        self.cell(0, 8, title, 0, 1)
        self.ln(1)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        x = self.get_x()
        self.cell(5, 6, '-', 0, 0)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def code_block(self, code):
        self.set_font('Courier', '', 9)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(40, 40, 40)
        # Split code into lines and handle long lines
        lines = code.strip().split('\n')
        # Calculate block height
        line_height = 5
        block_height = len(lines) * line_height + 6

        # Check if we need a new page
        if self.get_y() + block_height > 270:
            self.add_page()

        y_start = self.get_y()
        self.rect(10, y_start, 190, block_height, 'F')
        self.ln(3)
        for line in lines:
            # Truncate very long lines
            if len(line) > 90:
                line = line[:87] + '...'
            self.cell(5, line_height, '', 0, 0)
            self.cell(0, line_height, line, 0, 1)
        self.ln(4)

    def table_header(self, cols):
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(15, 52, 96)
        self.set_text_color(255, 255, 255)
        col_width = 190 / len(cols)
        for col in cols:
            self.cell(col_width, 8, col, 1, 0, 'C', True)
        self.ln()

    def table_row(self, cols, fill=False):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(40, 40, 40)
        if fill:
            self.set_fill_color(245, 245, 245)
        col_width = 190 / len(cols)
        for col in cols:
            self.cell(col_width, 7, col, 1, 0, 'C', fill)
        self.ln()


def generate_pdf():
    pdf = EcoSpherePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ==================== PAGE 1: COVER ====================
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(233, 69, 96)
    pdf.cell(0, 15, 'EcoSphere', 0, 1, 'C')
    pdf.set_font('Helvetica', '', 18)
    pdf.set_text_color(15, 52, 96)
    pdf.cell(0, 10, 'Real-Time Voice AI Sales Agent', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, 'Hackathon Project Document', 0, 1, 'C')
    pdf.cell(0, 8, 'Team: Winners4 | Round: II', 0, 1, 'C')
    pdf.ln(20)

    # Team details table
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(15, 52, 96)
    pdf.cell(0, 10, 'Team Members', 0, 1, 'C')
    pdf.ln(3)

    pdf.table_header(['Name', 'Role', 'Email'])
    members = [
        ['Sumodip Patra', 'Agent Brain (LangGraph)', 'sumodeeppatra@gmail.com'],
        ['Harsh Kalbande', 'Voice Pipeline Engineer', 'harshkalbande.10@gmail.com'],
        ['Kanishk Patil', 'Backend & Integration', 'kanishkpatil.kp21@gmail.com'],
        ['Yash Zunzurkar', 'Frontend, Demo Flow Lead', 'yashzunzurkar@gmail.com'],
    ]
    for i, member in enumerate(members):
        pdf.table_row(member, fill=(i % 2 == 0))

    # ==================== PAGE 2: PROBLEM & SOLUTION ====================
    pdf.add_page()
    pdf.section_title('1. Problem Statement')
    pdf.body_text(
        'Build a real-time voice AI sales agent that can conduct a complete '
        'customer qualification and sales conversation.'
    )

    pdf.sub_title('Problem Description')
    pdf.body_text(
        'Sales calls are scripted and brittle - bots break when customers interrupt, '
        'change requirements, or ask off-script questions. This creates poor customer '
        'experience. A real-time voice agent that understands, adapts, and remembers '
        'context throughout a live conversation can drive meaningful sales outcomes.'
    )

    pdf.sub_title('Proposed Solution')
    pdf.body_text(
        'We propose a real-time voice AI sales agent that conducts natural conversations '
        'instead of following fixed scripts. With Agora Conversational AI, we harness '
        'the AI agent to handle interruptions, change requirements, or maintain context '
        'like a real salesperson.'
    )
    pdf.body_text(
        'At its core is a Stateful LangGraph agent that maintains session memory across '
        'the entire call, and retrieves live product and pricing information through RAG. '
        'It is also integrated with a calendar to schedule meetings with human agents when '
        'the situation requires human intervention.'
    )

    pdf.sub_title('What Makes This Unique')
    pdf.bullet('Combining conversational memory, dynamic objection handling, and tool calling in one voice-native pipeline')
    pdf.bullet('Moving every call toward a clear, actionable outcome')
    pdf.bullet('Dynamic LangGraph routing instead of decision trees')
    pdf.bullet('Persistent memories instead of stateless turns')
    pdf.bullet('RAG-grounded answers instead of hallucination-prone free generation')

    # ==================== PAGE 3: ARCHITECTURE ====================
    pdf.add_page()
    pdf.section_title('2. System Architecture')

    pdf.sub_title('High-Level Flow')
    pdf.body_text(
        'Customer speaks -> Agora RTC Channel -> Agora ConvoAI Engine -> '
        'Your Custom LLM Server (LangGraph + RAG + Tools) -> Response -> TTS -> Customer'
    )

    pdf.sub_title('Components')
    pdf.bullet('Agora Voice Transport: Low-latency RTC channels connect customer to AI agent globally')
    pdf.bullet('Agora ConvoAI Engine: Orchestrates STT, LLM reasoning, and TTS in one flow')
    pdf.bullet('LangGraph Agent: Stateful multi-turn agent with memory and dynamic routing')
    pdf.bullet('RAG Knowledge Base: Product catalog + pricing info via ChromaDB vector search')
    pdf.bullet('Tool Calling: Calendar scheduling and product lookup')
    pdf.bullet('Frontend: Browser-based test UI for voice calls')

    pdf.sub_title('Agora Technology Utilization')
    pdf.table_header(['Feature', 'How It Works'])
    features = [
        ['Real-Time Voice Transport', 'Low-latency RTC globally'],
        ['ASR -> LLM -> TTS Pipeline', 'Agora ConvoAI orchestrates'],
        ['Interruption Handling', 'Voice detection stops agent'],
        ['Noise Suppression', '95% background noise filtered'],
        ['Selective Attention', 'Locks onto primary speaker'],
        ['Session Management', 'Channels, tokens, scheduling'],
    ]
    for i, feat in enumerate(features):
        pdf.table_row(feat, fill=(i % 2 == 0))

    # ==================== PAGE 4: WHAT'S BUILT ====================
    pdf.add_page()
    pdf.section_title('3. Current Status - What Is Built')

    pdf.sub_title('Existing Files')
    pdf.table_header(['File', 'Status', 'Description'])
    files = [
        ['voice_pipeline.py', 'BUILT', 'Agora pipeline (Deepgram->OpenAI->MiniMax)'],
        ['test_agora.py', 'BUILT', 'Simple Agora client test'],
        ['test_call.html', 'BUILT', 'Browser UI for voice calls'],
        ['text_call.html', 'BUILT', 'Browser UI with token'],
        ['.env', 'BUILT', 'Credentials (Agora App ID/Cert)'],
    ]
    for i, f in enumerate(files):
        pdf.table_row(f, fill=(i % 2 == 0))

    pdf.ln(5)
    pdf.sub_title('Key Code - voice_pipeline.py')
    pdf.code_block('''from agora_agent import Agent, Agora, Area, DeepgramSTT, OpenAI, MiniMaxTTS

client = Agora(area=Area.US, app_id="66d8b08d...",
               app_certificate="1e3fbbb8...")

agent = (
    Agent(client=client, turn_detection={"language": "en-US"})
    .with_stt(DeepgramSTT(model="nova-3", language="en"))
    .with_llm(OpenAI(model="gpt-4o-mini",
        system_messages=[{"role": "system", "content": AGENT_PROMPT}],
        greeting_message=GREETING, max_history=50,
        params={"max_tokens": 256, "temperature": 0.7}))
    .with_tts(MiniMaxTTS(model="speech_2_6_turbo",
        voice_id="English_captivating_female1"))
)

session = agent.create_session(
    channel=f"sales-call-{int(time.time())}",
    agent_uid="100001", remote_uids=["*"],
    idle_timeout=60, debug=True)

session.start()''')

    # ==================== PAGE 5: WHAT'S NEEDED ====================
    pdf.add_page()
    pdf.section_title('4. What Needs To Be Built')

    pdf.sub_title('Remaining Components')
    pdf.table_header(['Component', 'Priority', 'Owner', 'Status'])
    components = [
        ['LangGraph Stateful Agent', 'CRITICAL', 'Harsh (Voice)', 'NOT BUILT'],
        ['RAG Knowledge Base', 'CRITICAL', 'Sumodip (Brain)', 'NOT BUILT'],
        ['Interruption Handling', 'CRITICAL', 'Harsh (Voice)', 'NOT BUILT'],
        ['Calendar Integration', 'HIGH', 'Kanishk (Backend)', 'NOT BUILT'],
        ['Dynamic Objection Handling', 'HIGH', 'Sumodip (Brain)', 'NOT BUILT'],
        ['Frontend Dashboard', 'HIGH', 'Yash (Frontend)', 'NOT BUILT'],
        ['Analytics Dashboard', 'NICE-TO-HAVE', 'Team', 'NOT BUILT'],
        ['Multi-Language Support', 'NICE-TO-HAVE', 'Team', 'NOT BUILT'],
    ]
    for i, comp in enumerate(components):
        pdf.table_row(comp, fill=(i % 2 == 0))

    # ==================== PAGE 6: IMPLEMENTATION PLAN ====================
    pdf.add_page()
    pdf.section_title('5. Implementation Plan')

    pdf.sub_title('Architecture Overview')
    pdf.body_text(
        'Agora supports Custom LLM via OpenAI API-compatible endpoint. '
        'We wrap our LangGraph agent behind this endpoint:'
    )
    pdf.code_block('''Your LangGraph Agent
       |
       v
Custom LLM Server (FastAPI, OpenAI API format)
       |
       v
Agora ConvoAI Engine
       |
       v
Customer (via Agora RTC)''')

    pdf.sub_title('Step 1: Install Dependencies')
    pdf.code_block('''pip3 install langgraph langchain langchain-openai
pip3 install chromadb fastapi uvicorn
pip3 install python-dotenv''')

    pdf.sub_title('Step 2: Define Agent State (agent/state.py)')
    pdf.body_text(
        'The state holds conversation memory, customer info, and current intent:'
    )
    pdf.code_block('''from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    customer_info: dict
    current_intent: str
    handoff_needed: bool''')

    # ==================== PAGE 7: LANGGRAPH GRAPH ====================
    pdf.add_page()
    pdf.sub_title('Step 3: Build LangGraph Graph (agent/graph.py)')
    pdf.body_text(
        'The graph is a state machine that routes conversations:'
    )
    pdf.code_block('''from langgraph.graph import StateGraph

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("classify_intent", classify_intent)
graph.add_node("handle_pricing", handle_pricing)
graph.add_node("handle_objection", handle_objection)
graph.add_node("handle_demo", handle_demo)

# Add routing logic
graph.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "pricing": "handle_pricing",
        "objection": "handle_objection",
        "demo": "handle_demo",
        "general": "handle_general",
    }
)

graph.set_entry_point("classify_intent")''')

    pdf.sub_title('Step 4: Add Tool Calling (tools/)')
    pdf.code_block('''from langchain_core.tools import tool

@tool
def lookup_product(query: str) -> str:
    """Search product catalog for pricing info"""
    # Search ChromaDB, return product info
    results = product_db.similarity_search(query)
    return format_results(results)

@tool
def schedule_meeting(name: str, email: str, context: str) -> str:
    """Schedule a meeting with a human sales agent"""
    # Create calendar event with full call context
    return f"Meeting scheduled for {name}"''')

    # ==================== PAGE 8: FASTAPI SERVER ====================
    pdf.add_page()
    pdf.sub_title('Step 5: Create FastAPI Server (server/main.py)')
    pdf.body_text(
        'This server exposes your LangGraph agent as an OpenAI-compatible endpoint:'
    )
    pdf.code_block('''from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    # 1. Run LangGraph agent with user message
    result = agent_graph.invoke({
        "messages": request.messages,
        "customer_info": {},
        "current_intent": "",
        "handoff_needed": False
    })

    # 2. Stream response in OpenAI format
    async def generate():
        for chunk in result["response"]:
            yield f"data: {json.dumps(chunk)}\\n\\n"
        yield "data: [DONE]\\n\\n"

    return StreamingResponse(generate(),
        media_type="text/event-stream")''')

    pdf.sub_title('Step 6: Update Voice Pipeline (voice_pipeline.py)')
    pdf.code_block('''from agora_agent import Agent, Agora, Area, DeepgramSTT, MiniMaxTTS, CustomLLM

agent = (
    Agent(client=client, turn_detection={"language": "en-US"})
    .with_stt(DeepgramSTT(model="nova-3", language="en"))
    .with_llm(CustomLLM(
        api_key="your-key",
        base_url="http://localhost:8000/chat/completions",
        model="gpt-4o-mini",
        system_messages=[{"role": "system", "content": SALES_PROMPT}],
        greeting_message="Hi! I am your AI sales assistant...",
        max_history=50,
    ))
    .with_tts(MiniMaxTTS(model="speech_2_6_turbo",
        voice_id="English_captivating_female1"))
)''')

    # ==================== PAGE 9: INTERRUPTION HANDLING ====================
    pdf.add_page()
    pdf.section_title('6. Interruption Handling')

    pdf.sub_title('How Agora Handles Interruptions')
    pdf.body_text(
        'Agora ConvoAI Engine has built-in interruption support. '
        'Voice interruption is automatic - when the engine detects user voice input, '
        'it automatically stops the agent response.'
    )

    pdf.sub_title('Configuration')
    pdf.code_block('''agent = Agent(client=client)
.with_turn_detection({
    "mode": "default",
    "config": {
        "speech_threshold": 0.5,
        "start_of_speech": {
            "mode": "vad",
            "vad_config": {
                "interrupt_duration_ms": 160,
                "speaking_interrupt_duration_ms": 320,
                "prefix_padding_ms": 800,
            },
        },
        "end_of_speech": {
            "mode": "semantic",
            "semantic_config": {
                "silence_duration_ms": 320,
                "max_wait_ms": 3000,
            },
        },
    },
})''')

    pdf.sub_title('Manual Interruption')
    pdf.code_block('''# Server-side interrupt
session.interrupt()

# Or via REST API
# POST /agents/{agentId}/interrupt''')

    pdf.sub_title('Test Scenarios')
    pdf.table_header(['Scenario', 'Expected Behavior'])
    scenarios = [
        ['Customer talks over pricing', 'AI stops, addresses new question'],
        ['Customer says "wait" mid-sentence', 'AI yields immediately'],
        ['Customer stays silent', 'AI finishes response normally'],
        ['Customer changes topic', 'AI adapts to new topic'],
    ]
    for i, s in enumerate(scenarios):
        pdf.table_row(s, fill=(i % 2 == 0))

    # ==================== PAGE 10: RAG & TOOLS ====================
    pdf.add_page()
    pdf.section_title('7. RAG Knowledge Base')

    pdf.sub_title('Product Knowledge Structure')
    pdf.code_block('''# knowledge/products.json
{
    "products": [
        {
            "name": "Enterprise Plan",
            "price": "$99/month",
            "features": ["Unlimited calls", "Analytics", "Priority support"],
            "target": "Large teams"
        },
        {
            "name": "Pro Plan",
            "price": "$49/month",
            "features": ["1000 calls/mo", "Basic analytics"],
            "target": "Growing teams"
        }
    ]
}''')

    pdf.sub_title('ChromaDB Setup')
    pdf.code_block('''import chromadb

client = chromadb.Client()
collection = client.create_collection("products")

# Add product data
collection.add(
    documents=["Enterprise Plan at $99/month..."],
    metadatas=[{"type": "pricing"}],
    ids=["prod_1"]
)

# Query
results = collection.query(
    query_texts=["How much does enterprise cost?"],
    n_results=3
)''')

    pdf.section_title('8. Tool Calling')

    pdf.sub_title('Calendar Tool')
    pdf.code_block('''@tool
def schedule_meeting(customer_name: str, email: str,
                     topic: str, context: str) -> str:
    """Schedule a meeting with human sales agent"""
    # Integrate with Google Calendar API
    event = {
        "summary": f"Sales Follow-up: {customer_name}",
        "description": f"Context: {context}",
        "attendees": [{"email": email}],
    }
    # Create event and return confirmation
    return f"Meeting scheduled for {customer_name} at {email}"''')

    pdf.sub_title('Product Lookup Tool')
    pdf.code_block('''@tool
def lookup_product(query: str) -> str:
    """Search product catalog for information"""
    results = product_collection.query(
        query_texts=[query], n_results=3
    )
    return format_product_results(results)''')

    # ==================== PAGE 11: EXTENSIBILITY ====================
    pdf.add_page()
    pdf.section_title('9. Extensibility & Future Plans')

    pdf.sub_title('Beyond the Hackathon')
    pdf.bullet('Multi-language support using Agora multilingual ASR/TTS')
    pdf.bullet('Sentiment-based escalation triggers (not just keywords)')
    pdf.bullet('Analytics dashboard to track call outcomes and conversion rates')
    pdf.bullet('Generalize architecture to customer support, onboarding, appointment scheduling')
    pdf.bullet('Real CRM integration (Salesforce, HubSpot) instead of Google Sheets mock')

    pdf.sub_title('Validation')
    pdf.body_text(
        'We have mapped example scenarios (pricing questions, competitor interrupts, '
        'user count changes, enterprise demo requests) to specific nodes in our '
        'LangGraph design. We know precisely how each transition will be handled '
        'before we start building.'
    )

    pdf.sub_title('Constraints (Hackathon)')
    pdf.bullet('Google Sheets as mock CRM instead of live enterprise CRM')
    pdf.bullet('Same tool calling pattern extends to real CRM API in production')

    # ==================== PAGE 12: QUICK REFERENCE ====================
    pdf.add_page()
    pdf.section_title('10. Quick Reference - Key Commands')

    pdf.sub_title('Install Dependencies')
    pdf.code_block('''pip3 install langgraph langchain langchain-openai
pip3 install chromadb fastapi uvicorn python-dotenv
pip3 install agora-agents''')

    pdf.sub_title('Run the Server')
    pdf.code_block('''# Terminal 1: Start the LangGraph server
cd server
python3 main.py
# Server runs at http://localhost:8000

# Terminal 2: Start the voice pipeline
python3 voice_pipeline.py''')

    pdf.sub_title('Test the Voice Call')
    pdf.code_block('''# Open test_call.html in browser
# Paste the channel name from terminal
# Click "Join Call"
# Start speaking to the AI agent''')

    pdf.sub_title('Project Structure')
    pdf.code_block('''Winners4/
  |- agent/
  |    |- state.py          # Agent state definition
  |    |- graph.py          # LangGraph graph
  |- knowledge/
  |    |- products.json     # Product catalog
  |    |- rag.py            # RAG integration
  |- tools/
  |    |- calendar.py       # Meeting scheduling
  |    |- product_lookup.py # Product search
  |- server/
  |    |- main.py           # FastAPI server
  |- voice_pipeline.py      # Agora voice pipeline
  |- test_call.html         # Browser test UI
  |- .env                   # Credentials''')

    # Save
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "EcoSphere_Winners4_Document.pdf")
    pdf.output(output_path)
    print(f"PDF saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_pdf()
