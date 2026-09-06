# 🎙️ EcoSphere - Real-Time Voice AI Sales Agent

> **EchoSphere Hackathon** | Team: **Winners4**

A production-oriented voice AI sales agent that conducts natural, real-time sales conversations using Agora Conversational AI, LangGraph, and RAG-powered product knowledge.

---

## 🎯 What It Does

EcoSphere conducts **real-time voice sales calls** that feel natural:

- **Qualifies leads** by asking about needs, budget, and timeline
- **Answers pricing questions** accurately using RAG (no hallucination)
- **Handles objections** with empathy and provides relevant information
- **Schedules demos** with human agents when needed
- **Remembers context** throughout the entire conversation

## 🏗️ Architecture

```
Customer speaks → Agora RTC → Agora ConvoAI → FastAPI Server → LangGraph Agent
                                                       ↓
                                              ┌────────┴────────────────────────┐
                                              │  RAG Knowledge (ChromaDB)        │
                                              │  Product Tools + Calendar Tools  │
                                              │  Intent Router (6 intents)       │
                                              │  Objection Sub-Classification    │
                                              │  Slot Extraction (user_count,    │
                                              │    competitor, pricing tier)     │
                                              └────────┬────────────────────────┘
                                                       ↓
                                    ┌──────────────────┼──────────────────┐
                                    ↓                  ↓                  ↓
                               SqliteSaver      Slack Escalation    Dashboard
                              (persistent DB)   (human handoff)   (monitoring)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Agora account with App ID and Certificate
- Deepgram API key (for STT)
- MiniMax API key (for TTS)

### 1. Install Dependencies

```bash
pip3 install langgraph langchain langchain-groq fastapi uvicorn
pip3 install agora-token-builder python-dotenv
pip3 install agora-agents  # Agora's Python SDK
```

### 2. Configure Environment

Create `.env` file:
```env
AGORA_APP_ID=your_app_id
AGORA_APP_CERTIFICATE=your_certificate
LLM_SERVER_URL=http://localhost:8000

# For voice_agent.py (standalone Agora ConvoAI REST API)
AGORA_CUSTOMER_ID=your_customer_id
AGORA_CUSTOMER_SECRET=your_customer_secret
CONVOAI_PIPELINE_ID=your_pipeline_id
```

### 3. Run

**Option A: One-click start**
```bash
./start.sh
```

**Option B: Manual start**

Terminal 1 - Start the server:
```bash
python3 server/main.py
```

Terminal 2 - Start the voice pipeline:
```bash
python3 voice_pipeline.py
```

**Option C: Standalone REST API agent** (no SDK needed)
```bash
python3 voice_agent.py
python3 voice_agent.py --channel my-channel  # custom channel name
```

### 4. Make a Call

1. Copy the channel name from Terminal 2
2. Open `demo.html` in your browser
3. Paste the channel name and click "Join Call"
4. Start speaking to the AI agent!

## 📁 Project Structure

```
Winners4/
├── agent/
│   ├── graph.py              # LangGraph graph + objection sub-routing + SqliteSaver
│   ├── graph_with_tools.py   # Enhanced agent with RAG + tool calling
│   └── state.py              # Agent state with rich slots & objection records
├── knowledge/
│   ├── products.json         # Product catalog (3 plans, FAQs, competitors)
│   └── rag.py                # ChromaDB RAG integration
├── tools/
│   ├── calendar.py           # Meeting scheduling (mock + Google Calendar)
│   └── product_lookup.py     # Product search & voice-friendly formatting
├── server/
│   └── main.py               # FastAPI server + Slack escalation + session API
├── voice_pipeline.py         # Agora voice pipeline (SDK-based)
├── voice_agent.py            # 🆕 Agora voice agent (REST API, standalone)
├── dashboard.html            # 🆕 Monitoring dashboard (live transcripts, lead scores)
├── demo.html                 # Demo call UI
├── ARCHITECTURE.md           # 🆕 Mermaid architecture diagrams
├── start.sh                  # One-click startup
├── stop.sh                   # Stop all services
└── README.md                 # This file
```

## 🧠 How It Works

### Intent Classification
The agent classifies user intent in real-time:
- **Pricing** → Uses RAG to answer accurately from product catalog
- **Objection** → Sub-classified into Price/Trust/Competitor/Timing/Authority, escalates after 3 objections
- **Demo** → Collects info and schedules meeting
- **Competitor** → Professional differentiation without badmouthing
- **General** → Lead qualification with slot extraction (user_count, budget, timeline)

### Objection Sub-Classification
Each objection is categorized into a sub-type for smarter routing:
- 💰 **Price** → ROI-focused response + free trial offer
- 🔒 **Trust** → Security/SLA info + case studies
- ⚔️ **Competitor** → Professional comparison + discovery questions
- ⏰ **Timing** → Timeline exploration + follow-up scheduling
- 👔 **Authority** → Manager summary prep + include decision-maker

### RAG-Powered Answers
Instead of making up answers, the agent retrieves accurate product information:
```python
# Searches product catalog using ChromaDB
results = kb.search("How much does Enterprise cost?")
# Returns actual pricing from products.json
```

### Persistent Memory
All conversation state is saved to SQLite via LangGraph's SqliteSaver checkpointer. Sessions survive server restarts.

### Slot Extraction
The agent automatically extracts and tracks:
- `user_count` — team size mentioned by customer
- `pricing_tier_discussed` — which plan was discussed
- `competitor_mentioned` — which competitor was named
- `customer_info` — name, email, company, role, budget, timeline

### Slack Escalation
When objections pile up or a demo is requested, a full escalation payload is sent to Slack including:
- Customer info, conversation transcript, objection history
- Set `SLACK_WEBHOOK_URL` in `.env` to enable

### Tool Calling
The agent can use tools during conversation:
- `search_products(query)` - Find product information
- `get_pricing_summary()` - Get all pricing plans
- `schedule_meeting(...)` - Book demo with sales team
- `get_competitor_comparison(name)` - Compare against competitors

## 📊 Monitoring Dashboard

Open `dashboard.html` to see:
- **Live session list** with auto-refresh every 5s
- **Full transcripts** per session with customer/agent messages
- **Lead scoring** that updates based on engagement signals
- **Objection tracking** with sub-type classification
- **Slot values** — user_count, pricing tier, competitor mentioned
- **Escalation status** and outcome tracking

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Voice Transport | Agora RTC |
| Speech-to-Text | Deepgram Nova-3 |
| Text-to-Speech | MiniMax Turbo |
| Agent Framework | LangGraph |
| LLM | Groq (gpt-oss-20b) |
| RAG | ChromaDB (fallback: keyword search) |
| Backend | FastAPI |
| Frontend | Vanilla JS + Agora Web SDK |

## 👥 Team

| Name | Role |
|------|------|
| Sumodip Patra | Agent Brain (LangGraph) |
| Harsh Kalbande | Voice Pipeline Engineer |
| Kanishk Patil | Backend & Integration |
| Yash Zunzurkar | Frontend, Demo Flow Lead |

## 📝 License

---

**Built with ❤️ by Winners4**
