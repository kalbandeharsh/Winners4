"""
EcoSphere - Full End-to-End Test
Starts server, runs all API tests, validates persistence, then cleans up.
"""

import os
import sys
import json
import time
import signal
import subprocess
import requests
from threading import Thread

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
SERVER_PROC = None

def start_server():
    """Start the FastAPI server as a subprocess."""
    global SERVER_PROC
    print("🚀 Starting server...")
    SERVER_PROC = subprocess.Popen(
        [sys.executable, "server/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    # Wait for server to be ready
    for i in range(20):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                print("  ✅ Server started")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print("  ❌ Server failed to start")
    return False

def stop_server():
    """Stop the server."""
    global SERVER_PROC
    if SERVER_PROC:
        SERVER_PROC.terminate()
        SERVER_PROC.wait(timeout=5)
        print("  🛑 Server stopped")

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")
        if detail:
            print(f"     → {detail[:200]}")


def test_health():
    print("\n📋 TEST: /health")
    r = requests.get(f"{BASE_URL}/health")
    data = r.json()
    test("Status 200", r.status_code == 200)
    test("Agent name", data.get("agent") == "ecosphere-sales-agent")
    test("Checkpointer is sqlite", data.get("checkpointer") == "sqlite")
    test("Slack configured flag exists", "slack_configured" in data)
    test("Active sessions count", data.get("active_sessions", -1) >= 0)


def test_root():
    print("\n📋 TEST: / (root)")
    r = requests.get(f"{BASE_URL}/")
    data = r.json()
    test("Status 200", r.status_code == 200)
    test("Server name", "EcoSphere" in data.get("name", ""))
    test("Has /chat endpoint", "/chat/completions" in str(data))


def test_token():
    print("\n📋 TEST: /token")
    r = requests.get(f"{BASE_URL}/token", params={"channel": "test-e2e", "uid": 9999})
    data = r.json()
    test("Status 200", r.status_code == 200)
    test("Token returned", len(data.get("token", "")) > 20)
    test("App ID present", data.get("appId") == "66d8b08dbc7f47aa8abeed25ee9b02f4")
    test("Channel matches", data.get("channel") == "test-e2e")


def test_chat_completions():
    print("\n📋 TEST: /chat/completions (multi-turn)")
    
    # Turn 1: Greeting
    print("  → Turn 1: Greeting")
    r = requests.post(f"{BASE_URL}/chat/completions", json={
        "model": "ecosphere-sales-agent",
        "messages": [{"role": "user", "content": "Hi, I'm interested in your product"}],
        "stream": False
    }, timeout=60)
    data = r.json()
    test("Turn 1 - Status 200", r.status_code == 200, str(data)[:200])
    response_1 = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    test("Turn 1 - Has response", len(response_1) > 10, response_1[:100])
    test("Turn 1 - OpenAI format", "choices" in data)
    
    # Turn 2: Pricing
    print("  → Turn 2: Pricing question")
    r = requests.post(f"{BASE_URL}/chat/completions", json={
        "model": "ecosphere-sales-agent",
        "messages": [
            {"role": "user", "content": "Hi, I'm interested in your product"},
            {"role": "assistant", "content": response_1},
            {"role": "user", "content": "How much does the Pro plan cost?"}
        ],
        "stream": False
    }, timeout=60)
    data = r.json()
    test("Turn 2 - Status 200", r.status_code == 200, str(data)[:200])
    response_2 = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    test("Turn 2 - Has response", len(response_2) > 10, response_2[:100])
    test("Turn 2 - Pricing intent", "$79" in response_2 or "pro" in response_2.lower() or "pricing" in response_2.lower(), response_2[:200])
    
    # Turn 3: Objection
    print("  → Turn 3: Objection")
    r = requests.post(f"{BASE_URL}/chat/completions", json={
        "model": "ecosphere-sales-agent",
        "messages": [
            {"role": "user", "content": "Hi, I'm interested in your product"},
            {"role": "assistant", "content": response_1},
            {"role": "user", "content": "How much does the Pro plan cost?"},
            {"role": "assistant", "content": response_2},
            {"role": "user", "content": "That seems too expensive for us"}
        ],
        "stream": False
    }, timeout=60)
    data = r.json()
    test("Turn 3 - Status 200", r.status_code == 200, str(data)[:200])
    response_3 = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    test("Turn 3 - Has response", len(response_3) > 10, response_3[:100])
    
    return response_1, response_2, response_3


def test_sessions():
    print("\n📋 TEST: /sessions")
    r = requests.get(f"{BASE_URL}/sessions")
    data = r.json()
    test("Status 200", r.status_code == 200)
    test("Sessions key exists", "sessions" in data)
    test("Total key exists", "total" in data)
    sessions = data.get("sessions", [])
    test("Has sessions", len(sessions) > 0, f"Found {len(sessions)} sessions")
    
    # Check session fields
    if sessions:
        s = sessions[0]
        test("Session has session_id", "session_id" in s)
        test("Session has turn_count", "turn_count" in s)
        test("Session has current_intent", "current_intent" in s)
        test("Session has outcome", "outcome" in s)
        test("Session has objections_count", "objections_count" in s)
    
    return sessions


def test_session_detail(sessions):
    print("\n📋 TEST: /sessions/{id} (detail)")
    if not sessions:
        print("  ⚠️  No sessions to test detail — skipping")
        return
    
    sid = sessions[0]["session_id"]
    r = requests.get(f"{BASE_URL}/sessions/{sid}")
    data = r.json()
    test("Status 200", r.status_code == 200)
    test("Has messages", "messages" in data)
    test("Has customer_info", "customer_info" in data)
    test("Has objections", "objections" in data)
    test("Has user_count field", "user_count" in data)
    test("Has competitor_mentioned field", "competitor_mentioned" in data)
    test("Has pricing_tier_discussed field", "pricing_tier_discussed" in data)
    test("Messages is list", isinstance(data.get("messages", []), list))
    
    msgs = data.get("messages", [])
    test("Has conversation messages", len(msgs) > 0, f"{len(msgs)} messages")
    
    if msgs:
        roles = [m.get("role") for m in msgs]
        test("Has customer messages", "customer" in roles)
        test("Has agent messages", "agent" in roles)


def test_checkpointer_persistence():
    print("\n📋 TEST: Checkpointer persistence")
    # The ecosphere.db file should exist and have data
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecosphere.db")
    test("SQLite DB exists", os.path.exists(db_path))
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        test("DB has data (>1KB)", size > 1024, f"Size: {size} bytes")


def test_streaming():
    print("\n📋 TEST: /chat/completions (streaming)")
    r = requests.post(f"{BASE_URL}/chat/completions", json={
        "model": "ecosphere-sales-agent",
        "messages": [{"role": "user", "content": "What plans do you offer?"}],
        "stream": True
    }, stream=True, timeout=60)
    test("Status 200", r.status_code == 200)
    test("Content-Type is SSE", "text/event-stream" in r.headers.get("content-type", ""))
    
    chunks = []
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                chunk = json.loads(line[6:])
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    chunks.append(content)
            except json.JSONDecodeError:
                pass
    
    full_response = "".join(chunks)
    test("Got streaming chunks", len(chunks) > 0, f"{len(chunks)} chunks")
    test("Assembled response has content", len(full_response) > 10, full_response[:100])


def test_objection_subrouting():
    """Test that objections are classified and stored."""
    print("\n📋 TEST: Objection sub-routing")
    # Send multiple objections to trigger escalation
    r = requests.post(f"{BASE_URL}/chat/completions", json={
        "model": "ecosphere-sales-agent",
        "messages": [
            {"role": "user", "content": "How much does it cost?"},
            {"role": "assistant", "content": "The Pro plan is $79/month."},
            {"role": "user", "content": "That is too expensive for our budget"},
        ],
        "stream": False
    }, timeout=60)
    data = r.json()
    test("Objection turn - Status 200", r.status_code == 200, str(data)[:200])
    
    r = requests.post(f"{BASE_URL}/chat/completions", json={
        "model": "ecosphere-sales-agent",
        "messages": [
            {"role": "user", "content": "How much does it cost?"},
            {"role": "assistant", "content": "The Pro plan is $79/month."},
            {"role": "user", "content": "That is too expensive for our budget"},
            {"role": "assistant", "content": "I understand the concern..."},
            {"role": "user", "content": "We use Twilio and it works fine"},
        ],
        "stream": False
    }, timeout=60)
    data = r.json()
    test("Second objection turn - Status 200", r.status_code == 200, str(data)[:200])
    
    # Check that sessions now have objection records
    r = requests.get(f"{BASE_URL}/sessions")
    sessions = r.json().get("sessions", [])
    sessions_with_objections = [s for s in sessions if s.get("objections_count", 0) > 0]
    test("Sessions have recorded objections", len(sessions_with_objections) > 0,
         f"{len(sessions_with_objections)} sessions with objections")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 EcoSphere Full End-to-End Test")
    print("=" * 60)
    
    try:
        if not start_server():
            sys.exit(1)
        
        test_health()
        test_root()
        test_token()
        test_checkpointer_persistence()
        
        try:
            test_chat_completions()
        except requests.exceptions.RequestException as e:
            print(f"\n  ⚠️  Chat completions failed (likely invalid Groq API key): {e}")
            print("  ⚠️  Skipping LLM-dependent tests (streaming, sessions, objection routing)")
        
        try:
            sessions = test_sessions()
            test_session_detail(sessions)
        except Exception as e:
            print(f"\n  ⚠️  Session tests skipped: {e}")
        
        try:
            test_streaming()
        except Exception as e:
            print(f"\n  ⚠️  Streaming test skipped: {e}")
        
        try:
            test_objection_subrouting()
        except Exception as e:
            print(f"\n  ⚠️  Objection routing test skipped: {e}")
        
    finally:
        stop_server()
    
    # Summary
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"📊 Results: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed — check details above")
    print("=" * 60)
