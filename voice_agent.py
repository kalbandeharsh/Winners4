"""
EcoSphere - Agora ConvoAI Voice Agent (Standalone)

Standalone script that uses the Agora Conversational AI REST API to create
and join a voice agent session. This is an alternative to voice_pipeline.py
(which uses the agora_agent Python SDK).

Usage:
    python3 voice_agent.py                        # Use defaults from .env
    python3 voice_agent.py --channel my-channel   # Override channel name
    python3 voice_agent.py --uid 12345            # Override agent UID

Required .env vars:
    AGORA_APP_ID            - Agora App ID
    AGORA_APP_CERTIFICATE   - Agora App Certificate (for RTC token generation)
    AGORA_CUSTOMER_ID       - Agora Customer ID (for REST API Basic Auth)
    AGORA_CUSTOMER_SECRET   - Agora Customer Secret (for REST API Basic Auth)
    CONVOAI_PIPELINE_ID     - Pipeline ID from the Agora console

Optional .env vars:
    CONVOAI_AGENT_NAME      - Agent name (default: eco-agent-<timestamp>)
    CONVOAI_AGENT_UID       - Agent RTC UID (default: 83705447)
    CONVOAI_IDLE_TIMEOUT    - Idle timeout in seconds (default: 60)
"""

import argparse
import base64
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv
from agora_token_builder import RtcTokenBuilder

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
AGORA_APP_ID = os.getenv("AGORA_APP_ID", "")
AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE", "")
AGORA_CUSTOMER_ID = os.getenv("AGORA_CUSTOMER_ID", "")
AGORA_CUSTOMER_SECRET = os.getenv("AGORA_CUSTOMER_SECRET", "")
CONVOAI_PIPELINE_ID = os.getenv("CONVOAI_PIPELINE_ID", "")
CONVOAI_AGENT_NAME = os.getenv("CONVOAI_AGENT_NAME", "")
CONVOAI_AGENT_UID = os.getenv("CONVOAI_AGENT_UID", "83705447")
CONVOAI_IDLE_TIMEOUT = int(os.getenv("CONVOAI_IDLE_TIMEOUT", "60"))

# Agora ConvoAI API base
CONVOAI_BASE_URL = "https://api.agora.io/api/conversational-ai-agent/v2"


def _make_basic_auth(customer_id: str, customer_secret: str) -> str:
    """Create Basic Auth header value from Customer ID and Secret."""
    credentials = f"{customer_id}:{customer_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def _generate_rtc_token(app_id: str, app_certificate: str, channel: str, uid: int) -> str:
    """Generate an RTC token valid for 24 hours."""
    now = int(time.time())
    token = RtcTokenBuilder.buildTokenWithUid(
        app_id, app_certificate, channel, uid,
        1, now + 86400  # 24 hours
    )
    return token


def join_voice_agent(
    pipeline_id: str,
    channel: str,
    agent_name: str = "",
    agent_uid: str = "83705447",
    idle_timeout: int = 60,
) -> dict:
    """
    Create and join an Agora ConvoAI voice agent session.

    Args:
        pipeline_id:   The ConvoAI pipeline ID from the Agora console.
        channel:       The RTC channel name to join.
        agent_name:    Optional agent name (auto-generated if empty).
        agent_uid:     The agent's RTC UID.
        idle_timeout:  Seconds of inactivity before the agent leaves.

    Returns:
        The API response as a dict.

    Raises:
        RuntimeError: If the API call fails.
    """
    if not agent_name:
        agent_name = f"eco-agent-{int(time.time())}"

    # Generate RTC token for joining the channel
    rtc_token = _generate_rtc_token(AGORA_APP_ID, AGORA_APP_CERTIFICATE, channel, int(agent_uid))

    url = f"{CONVOAI_BASE_URL}/projects/{AGORA_APP_ID}/join"
    headers = {
        "Authorization": _make_basic_auth(AGORA_CUSTOMER_ID, AGORA_CUSTOMER_SECRET),
        "Content-Type": "application/json",
    }
    data = {
        "name": agent_name,
        "pipeline_id": pipeline_id,
        "properties": {
            "channel": channel,
            "agent_rtc_uid": agent_uid,
            "remote_rtc_uids": ["*"],
            "token": rtc_token,
        },
    }

    print(f"📡 Joining ConvoAI session...")
    print(f"   Pipeline : {pipeline_id}")
    print(f"   Channel  : {channel}")
    print(f"   Agent    : {agent_name} (UID: {agent_uid})")
    print(f"   Timeout  : {idle_timeout}s")

    response = requests.post(url, json=data, headers=headers, timeout=30)
    response.raise_for_status()

    result = response.json()
    print(f"✅ Agent joined successfully!")
    print(f"   Response: {json.dumps(result, indent=2)}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="EcoSphere - Agora ConvoAI Voice Agent (Standalone)"
    )
    parser.add_argument(
        "--channel",
        type=str,
        default=None,
        help="RTC channel name (default: sales-call-<timestamp>)",
    )
    parser.add_argument(
        "--pipeline-id",
        type=str,
        default=None,
        help="ConvoAI pipeline ID (default: from CONVOAI_PIPELINE_ID env var)",
    )
    parser.add_argument(
        "--uid",
        type=str,
        default=None,
        help="Agent RTC UID (default: 83705447)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Agent name (default: eco-agent-<timestamp>)",
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=None,
        help="Idle timeout in seconds (default: 60)",
    )
    args = parser.parse_args()

    # Resolve values: CLI args > env vars > defaults
    pipeline_id = args.pipeline_id or CONVOAI_PIPELINE_ID
    channel = args.channel or f"sales-call-{int(time.time())}"
    agent_uid = args.uid or CONVOAI_AGENT_UID
    agent_name = args.name or CONVOAI_AGENT_NAME
    idle_timeout = args.idle_timeout or CONVOAI_IDLE_TIMEOUT

    # Validate required values
    missing = []
    if not AGORA_APP_ID:
        missing.append("AGORA_APP_ID")
    if not AGORA_APP_CERTIFICATE:
        missing.append("AGORA_APP_CERTIFICATE")
    if not AGORA_CUSTOMER_ID:
        missing.append("AGORA_CUSTOMER_ID")
    if not AGORA_CUSTOMER_SECRET:
        missing.append("AGORA_CUSTOMER_SECRET")
    if not pipeline_id:
        missing.append("CONVOAI_PIPELINE_ID")

    if missing:
        print(f"❌ Missing required env vars: {', '.join(missing)}")
        print("   Add them to your .env file.")
        if "AGORA_CUSTOMER_ID" in missing or "AGORA_CUSTOMER_SECRET" in missing:
            print("   Find Customer ID/Secret in Agora Console → Account → API Credentials")
        if "CONVOAI_PIPELINE_ID" in missing:
            print("   Find Pipeline ID in Agora Console → Agents → your agent → Code tab")
        sys.exit(1)

    try:
        result = join_voice_agent(
            pipeline_id=pipeline_id,
            channel=channel,
            agent_name=agent_name,
            agent_uid=agent_uid,
            idle_timeout=idle_timeout,
        )
        print()
        print("=" * 50)
        print(f"🎙️  CHANNEL NAME: {channel}")
        print("=" * 50)
        print("📋 Copy the channel name above and paste it in test_call.html")
        print("🎙️  Voice agent is running! Press Ctrl+C to stop.")
    except requests.exceptions.HTTPError as e:
        print(f"❌ API error: {e}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
