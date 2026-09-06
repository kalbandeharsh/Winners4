import os
import time
from dotenv import load_dotenv
from agora_agent import Agent, Agora, Area, DeepgramSTT, CustomLLM, MiniMaxTTS

load_dotenv()

# Server URL - use ngrok URL for Agora (cloud can't reach localhost)
# Start ngrok: ngrok http 8000
# Then paste the https URL below or in .env as LLM_SERVER_URL
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://localhost:8000")

AGENT_PROMPT = """You are a friendly AI sales assistant.
Qualify the lead: understand their needs, budget, and timeline.
Keep responses short and conversational."""

GREETING = "Hi! I'm your AI sales assistant. How can I help you today?"

AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERT = os.getenv("AGORA_APP_CERTIFICATE")
if not AGORA_APP_ID or not AGORA_APP_CERT:
    raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE must be set in .env")

client = Agora(area=Area.US, app_id=AGORA_APP_ID,
               app_certificate=AGORA_APP_CERT)

# LangGraph agent via FastAPI server (run server first: python3 server/main.py)
agent = (
    Agent(client=client, turn_detection={"language": "en-US"})
    .with_stt(DeepgramSTT(model="nova-3", language="en"))
    .with_llm(CustomLLM(
        api_key="not-needed",
        base_url=f"{LLM_SERVER_URL}/chat/completions",
        model="ecosphere-sales-agent",
        system_messages=[{"role": "system", "content": AGENT_PROMPT}],
        greeting_message=GREETING,
        max_history=50,
        params={"max_tokens": 256, "temperature": 0.7}))
    .with_tts(MiniMaxTTS(model="speech_2_6_turbo",
        voice_id="English_captivating_female1"))
)

channel_name = f"sales-call-{int(time.time())}"

session = agent.create_session(
    channel=channel_name,
    agent_uid="100001", remote_uids=["*"],
    name=f"conversation-{int(time.time())}",
    idle_timeout=60, debug=True)

print("=" * 50)
print(f"🎙️ CHANNEL NAME: {channel_name}")
print("=" * 50)
print("📋 Copy the channel name above and paste it in test_call.html")
print("🎙️ Voice pipeline started! Press Ctrl+C to stop.")
session.start()