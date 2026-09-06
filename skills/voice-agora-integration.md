---
name: voice-agora-integration
description: Guide for the Voice / Agora Integration role on the TrustLine (Voice AI Sales Agent) hackathon project. Covers configuring Agora's Conversational AI Engine — RTC transport, ASR, TTS, VAD, and interruption handling — and connecting it to the backend LLM endpoint. Use this skill whenever working on Agora setup, voice pipeline configuration, barge-in/interruption behavior, or RTC app credentials for this project.
---

# Role: Voice / Agora Integration

## Purpose of this role
You own the audio layer end to end — everything between the customer's microphone and the backend that runs the agent's brain. Your work is what makes the conversation *feel* real-time and natural: fast transcription, natural speech playback, and instant interruption handling.

You are **not** responsible for: what the agent says (that's the LangGraph/Agent Brain role), where product/pricing data comes from (RAG role), or the webhook server code itself (Backend/Frontend role) — though you will hand off directly to that server.

---

## Prerequisite knowledge (read this first if unfamiliar)
- **RTC** = Real-Time Communication — the technology that streams audio with very low delay (like a phone call, not like sending a voice message).
- **ASR** = Automatic Speech Recognition — converts spoken audio into text.
- **TTS** = Text-to-Speech — converts text into spoken audio.
- **VAD** = Voice Activity Detection — detects when someone is speaking vs. silent, used to know when a turn starts/ends.
- **Barge-in / interruption handling** = the ability for the customer to start speaking while the agent is still talking, and have the agent immediately stop and listen.

---

## Step-by-step guide

### Step 1 — Get Agora project credentials
- [ ] Sign up / log in at the Agora Console
- [ ] Create a new project for this hackathon
- [ ] Note down: **App ID**, **App Certificate**
- [ ] Store these securely — share with Person 4 (backend) via a shared `.env` file, never commit to a public repo

> Space to fill in:
> - App ID: `______________________`
> - App Certificate: `______________________`
> - Project name: `______________________`

### Step 2 — Enable Conversational AI Engine
- [ ] In the Agora Console, enable the **Conversational AI Engine** feature for your project
- [ ] Review available ASR vendor options and pick one (document your choice + why)
- [ ] Review available TTS vendor options and pick one (document your choice + why)

> Space to fill in:
> - ASR vendor chosen: `______________________` Reason: `______________________`
> - TTS vendor chosen: `______________________` Reason: `______________________`

### Step 3 — Configure the LLM endpoint connection
This is the critical handoff point to the rest of the team. Agora's engine needs to know where to send transcribed text and where to get the agent's reply from.

- [ ] Get the backend webhook URL from Person 4 (e.g., `https://your-backend-url/agora-webhook`)
- [ ] Configure Agora's engine to call this endpoint as its "custom LLM" / "LLM endpoint" target
- [ ] Confirm the expected request/response format with Person 4 (usually JSON: `{ "session_id": ..., "text": ... }` in, `{ "response": ... }` out)

> Space to fill in:
> - Backend webhook URL: `______________________`
> - Confirmed request format: `______________________`

### Step 4 — Build a minimal test app
- [ ] Set up a simple web page (Agora provides RTC SDK quickstart samples) that can join a call and stream audio
- [ ] Test: join the call, speak, confirm audio is captured and streamed
- [ ] Test: confirm ASR is producing transcribed text (check logs/console)

### Step 5 — Test interruption / barge-in behavior
- [ ] While the agent (or a placeholder response) is speaking, interrupt by talking
- [ ] Confirm TTS playback stops immediately when interruption is detected
- [ ] Tune VAD sensitivity if interruptions are too eager (cutting off normal pauses) or too slow (not detecting real interruptions)

> Notes on tuning:
> `______________________`

### Step 6 — Noise handling check
- [ ] Test in a moderately noisy environment (background chatter, typing, etc.)
- [ ] Confirm Agora's built-in noise suppression / echo cancellation is active and working acceptably

### Step 7 — Full pipeline test with the real backend
- [ ] Once Person 4's backend is live and Person 2's LangGraph brain is wired in, run a full end-to-end call
- [ ] Verify: customer speaks → ASR transcribes → backend calls LangGraph → response returns → TTS speaks it → customer hears it
- [ ] Measure round-trip latency (should feel conversational, not delayed)

> Latency notes: `______________________`

---

## Handoff checklist (what other roles need from you)
- [ ] Working Agora App ID + Certificate shared with the team
- [ ] Confirmed request/response JSON contract shared with Person 4 (backend)
- [ ] A test call script/demo the team can use to sanity-check the pipeline anytime
- [ ] Documented ASR/TTS vendor choices for the idea-submission write-up

## Common pitfalls
- Forgetting to test barge-in specifically — it's easy to build a pipeline that works for simple Q&A but breaks the moment someone interrupts.
- Not confirming the JSON contract early with the backend owner — mismatched formats cause silent failures.
- Testing only in silence — always test with background noise since real demo conditions (stage mic, audience noise) won't be silent.
