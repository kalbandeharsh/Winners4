"""
EcoSphere - Barge-In / Interruption Test Script
================================================
Tests that the voice pipeline correctly handles interruptions:
when the customer speaks while the agent is talking, the TTS should
stop immediately and the agent should listen to the new input.

How to use:
1. Start the server: python3 server/main.py
2. Start the voice pipeline: python3 voice_pipeline.py
3. Open test_call.html, paste the channel name, and join
4. When the agent starts speaking, interrupt by talking
5. Watch the terminal output for interruption detection

What to verify:
- Agent TTS stops immediately when you speak
- Your new speech is transcribed (ASR picks it up)
- Agent responds to your interruption, not the old message
- No audio overlap (agent and customer not talking simultaneously)

VAD Tuning Notes:
- Default VAD in Agora ConvoAI should work for most cases
- If interruptions are too eager (cutting off normal pauses):
  → Increase silence threshold in Agora Console settings
- If interruptions are too slow (not detecting real ones):
  → Decrease silence threshold or increase sensitivity
- Key setting: "Minimum speech duration" controls how long you
  must speak before an interruption is recognized
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

load_dotenv()

AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERT = os.getenv("AGORA_APP_CERTIFICATE")

if not AGORA_APP_ID or not AGORA_APP_CERT:
    print("❌ AGORA_APP_ID and AGORA_APP_CERTIFICATE must be set in .env")
    sys.exit(1)

try:
    from agora_agent import Agent, Agora, Area, DeepgramSTT, CustomLLM, MiniMaxTTS
except ImportError:
    print("❌ agora-agent SDK not installed. Run: pip3 install agora-agents")
    sys.exit(1)

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://localhost:8000")

AGENT_PROMPT = """You are a friendly AI sales assistant.
Qualify the lead: understand their needs, budget, and timeline.
Keep responses short and conversational.
IMPORTANT: If the customer interrupts you, stop talking immediately and respond to what they said."""

GREETING = "Hi! I'm your AI sales assistant. I'm here to help you learn about our product. How can I help you today?"

client = Agora(area=Area.US, app_id=AGORA_APP_ID, app_certificate=AGORA_APP_CERT)

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

channel_name = f"barge-in-test-{int(time.time())}"

print("=" * 60)
print("🎙️  BARGE-IN / INTERRUPTION TEST")
print("=" * 60)
print(f"📡 Channel: {channel_name}")
print()
print("INSTRUCTIONS:")
print("  1. Open test_call.html in your browser")
print(f"  2. Paste channel name: {channel_name}")
print("  3. Click 'Join Call'")
print("  4. Let the agent start speaking, then INTERRUPT by talking")
print("  5. Verify the agent stops and responds to your interruption")
print()
print("What to watch for in terminal output:")
print("  - '🔴 Interruption detected' or similar when you speak over agent")
print("  - Your interrupted speech is transcribed")
print("  - Agent responds to your new input")
print()
print("Press Ctrl+C to stop the test.")
print("=" * 60)

session = agent.create_session(
    channel=channel_name,
    agent_uid="100001",
    remote_uids=["*"],
    name=f"barge-in-test-{int(time.time())}",
    idle_timeout=60,
    debug=True  # Enable debug logging to see interruption events
)

session.start()
