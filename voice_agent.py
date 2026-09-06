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
    AGORA_TOKEN             - Bearer token for Agora Conversational AI API
    CONVOAI_PIPELINE_ID     - Pipeline ID from the Agora console

Optional .env vars:
    CONVOAI_AGENT_NAME      - Agent name (default: eco-agent-<timestamp>)
    CONVOAI_AGENT_UID       - Agent RTC UID (default: 83705447)
    CONVOAI_IDLE_TIMEOUT    - Idle timeout in seconds (default: 60)
"""

import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
AGORA_TOKEN = os.getenv("AGORA_TOKEN", "")
CONVOAI_PIPELINE_ID = os.getenv("CONVOAI_PIPELINE_ID", "")
CONVOAI_AGENT_NAME = os.getenv("CONVOAI_AGENT_NAME", "")
CONVOAI_AGENT_UID = os.getenv("CONVOAI_AGENT_UID", "83705447")
CONVOAI_IDLE_TIMEOUT = int(os.getenv("CONVOAI_IDLE_TIMEOUT", "60"))

# Agora ConvoAI API base
CONVOAI_BASE_URL = "https://api.agora.io/api/conversational-ai-agent/v2"


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

    url = f"{CONVOAI_BASE_URL}/projects/716291267cab4ad2913563d237964e6e/join"
    headers = {
        "Authorization": f"agora token={AGORA_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "name": agent_name,
        "pipeline_id": pipeline_id,
        "properties": {
            "agent_rtc_uid": agent_uid,
            "channel": channel,
            "enable_string_uid": False,
            "idle_timeout": idle_timeout,
            "remote_rtc_uids": ["*"],
            "token": AGORA_TOKEN,
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
    if not AGORA_TOKEN:
        print("❌ AGORA_TOKEN not set. Add it to your .env file.")
        sys.exit(1)
    if not pipeline_id:
        print("❌ CONVOAI_PIPELINE_ID not set. Add it to your .env file.")
        print("   Find it in the Agora Console → Agents → Pipeline tab.")
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
