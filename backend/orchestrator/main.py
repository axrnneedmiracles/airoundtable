import os
import re
import sys
import base64
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure backend root is on sys.path for local module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from persona_store.models import PERSONAS, get_persona, Persona
from tools.whisper import call_whisper
from tools.elevenlabs_tts import synthesize, set_elevenlabs_api_key, get_tts_status, PERSONA_VOICES
from tools.finetune_dataset import export_finetune_dataset
from llm_worker.agent import generate_agent_response, OLLAMA_MODEL, OLLAMA_HOST, LLM_MODEL, LLM_API_BASE
from orchestrator.a2a_protocol import A2AMessage, A2AIntent, A2ARoundtableCoordinator
from orchestrator.topic_engine import TopicEngine, DEFAULT_TOPIC
from orchestrator.memory_engine import DebateMemoryEngine

app = FastAPI(title="AI Roundtable - Real-Time Multi-Agent Podcast")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse(frontend_dir / "index.html")

# Global Roundtable State & Memory Engines
ROUNDTABLE_LOCK = asyncio.Lock()
coordinator = A2ARoundtableCoordinator()
topic_engine = TopicEngine(DEFAULT_TOPIC)
memory_engine = DebateMemoryEngine(DEFAULT_TOPIC)

PODCAST_STATE = {
    "topic": DEFAULT_TOPIC,
    "is_running": False,
    "active_speaker": None,
    "history": [],
    "a2a_traces": [],
    "audio_queue": []
}

active_connections: List[WebSocket] = []

async def broadcast_event(event_type: str, data: Any):
    payload = {"type": event_type, "data": data}
    dead = []
    for conn in list(active_connections):
        try:
            await asyncio.wait_for(conn.send_json(payload), timeout=1.5)
        except Exception:
            dead.append(conn)
    for d in dead:
        if d in active_connections:
            active_connections.remove(d)

def get_last_speaker_id() -> Optional[str]:
    """Finds the last valid panelist who spoke from active state or history."""
    agent_cycle = ["host", "technologist", "ethicist"]
    current = PODCAST_STATE.get("active_speaker")
    if current in agent_cycle:
        return current
    for item in reversed(PODCAST_STATE.get("history", [])):
        aid = item.get("agent_id")
        if aid in agent_cycle:
            return aid
    return None

@app.get("/api/state")
async def get_state():
    return PODCAST_STATE

@app.get("/api/personas")
async def get_personas():
    return {k: v.dict() for k, v in PERSONAS.items()}

@app.get("/api/a2a/traces")
async def get_a2a_traces():
    return coordinator.get_recent_traces(30)

@app.get("/api/memory")
async def get_memory_state():
    """Returns full episodic memory, persona claims ledger, and debate narrative summary."""
    return {
        "stats": memory_engine.get_stats(),
        "claims_ledger": memory_engine.claims_ledger,
        "narrative_summary": memory_engine.narrative_summary,
        "audience_interventions": memory_engine.audience_interventions,
        "turns_count": len(memory_engine.turns)
    }

@app.get("/api/config")
async def get_configuration():
    """Returns status of LLM engine, STT whisper engine, and ElevenLabs TTS."""
    return {
        "llm": {
            "ollama_host": OLLAMA_HOST,
            "ollama_model": OLLAMA_MODEL,
            "cloud_model": LLM_MODEL,
            "cloud_base": LLM_API_BASE or "Direct OpenAI"
        },
        "tts": get_tts_status(),
        "stt": {
            "local_whisper_url": os.getenv("WHISPER_SERVER_URL", "http://127.0.0.1:8080/inference"),
            "groq_whisper_active": bool(os.getenv("GROQ_API_KEY")),
            "openai_whisper_active": bool(os.getenv("OPENAI_API_KEY"))
        },
        "memory_turns": len(memory_engine.turns)
    }

@app.post("/api/config/tts")
async def update_tts_config(api_key: str = Form(...)):
    """Dynamically updates ElevenLabs API key at runtime."""
    set_elevenlabs_api_key(api_key, persist_to_env=True)
    return {
        "status": "updated",
        "tts": get_tts_status()
    }

@app.get("/api/finetune/export")
async def export_dataset(format: str = Query("openai")):
    """Exports recorded turns as fine-tuning dataset."""
    turns_for_export = []
    # Build export entries from memory engine
    for t in memory_engine.turns:
        if t.speaker_name in ["Sarah", "Charlie", "Roger"]:
            turns_for_export.append({
                "topic": memory_engine.topic,
                "persona": t.speaker_id,
                "system": PERSONAS[t.speaker_id].system_prompt,
                "history": [
                    {"sender": prev.speaker_name, "content": prev.content}
                    for prev in memory_engine.turns[:t.turn_index - 1][-4:]
                ],
                "instruction": f"Speak as {t.speaker_name} on {t.dimension}",
                "response": t.content
            })

    out_file = export_finetune_dataset(
        turns_source=turns_for_export if turns_for_export else None,
        export_format=format
    )
    return FileResponse(out_file, filename=Path(out_file).name, media_type="application/jsonl")

@app.get("/api/topics")
async def get_curated_topics():
    from orchestrator.topic_engine import THEMATIC_BLUEPRINTS
    topics = []
    for key, data in THEMATIC_BLUEPRINTS.items():
        topics.append({
            "key": key,
            "title": data["title"],
            "category": data.get("category", "Debate"),
            "battlegrounds_count": len(data.get("battlegrounds", []))
        })
    return {"topics": topics, "current": PODCAST_STATE["topic"]}

@app.post("/api/topic")
async def set_topic(topic: str = Form(...), clear_history: bool = Form(False)):
    global topic_engine, memory_engine
    clean_topic = topic.strip()
    PODCAST_STATE["topic"] = clean_topic
    topic_engine = TopicEngine(clean_topic)
    memory_engine.set_topic(clean_topic, clear_history=clear_history)

    if clear_history:
        PODCAST_STATE["history"] = []
        PODCAST_STATE["a2a_traces"] = []
        PODCAST_STATE["active_speaker"] = None
        PODCAST_STATE["audio_queue"] = []
        coordinator.clear()
        await broadcast_event("history_cleared", {"topic": clean_topic})
    else:
        system_turn = {
            "sender": "System",
            "role": "Topic Change",
            "content": f"The podcast topic was updated to: '{clean_topic}'"
        }
        PODCAST_STATE["history"].append(system_turn)

    await broadcast_event("topic_updated", {"topic": clean_topic, "cleared": clear_history})
    return {"status": "ok", "topic": clean_topic}

@app.post("/api/history/clear")
async def clear_history():
    PODCAST_STATE["history"] = []
    PODCAST_STATE["a2a_traces"] = []
    PODCAST_STATE["active_speaker"] = None
    PODCAST_STATE["audio_queue"] = []
    coordinator.clear()
    memory_engine.clear()
    await broadcast_event("history_cleared", {"status": "cleared"})
    return {"status": "cleared", "history": []}

@app.post("/api/conversation/new")
async def start_new_conversation(topic: Optional[str] = Form(None)):
    """Starts a completely fresh roundtable conversation, clearing all memory, claims, traces, and state."""
    global topic_engine, memory_engine
    new_topic = (topic or "").strip() or PODCAST_STATE.get("topic", DEFAULT_TOPIC)

    PODCAST_STATE["topic"] = new_topic
    PODCAST_STATE["history"] = []
    PODCAST_STATE["a2a_traces"] = []
    PODCAST_STATE["active_speaker"] = None
    PODCAST_STATE["audio_queue"] = []
    PODCAST_STATE["is_running"] = False

    coordinator.clear()
    memory_engine.clear()
    memory_engine.set_topic(new_topic, clear_history=True)
    topic_engine = TopicEngine(new_topic)

    payload = {
        "status": "ok",
        "topic": new_topic,
        "message": "New conversation initialized."
    }
    await broadcast_event("new_conversation", payload)
    await broadcast_event("history_cleared", {"topic": new_topic, "status": "cleared"})
    return payload

@app.post("/api/podcast/start")
async def start_podcast():
    PODCAST_STATE["is_running"] = True
    await broadcast_event("podcast_status", {"is_running": True})
    return {"status": "started"}

@app.post("/api/podcast/stop")
async def stop_podcast():
    PODCAST_STATE["is_running"] = False
    PODCAST_STATE["active_speaker"] = None
    await broadcast_event("podcast_status", {"is_running": False})
    return {"status": "stopped"}

@app.post("/api/turn/trigger")
async def trigger_turn(target_agent: Optional[str] = None):
    """Executes a round-table turn using A2A negotiation, episodic memory, and ElevenLabs voice synthesis."""
    # 1. State resolution inside short critical section
    async with ROUNDTABLE_LOCK:
        agent_cycle = ["host", "technologist", "ethicist"]
        last_agent = get_last_speaker_id()

        # A2A Turn Deliberation
        if not target_agent or target_agent not in PERSONAS:
            if not PODCAST_STATE["history"]:
                target_agent = "host"
                a2a_intent = A2AIntent.OPEN_ROUNDTABLE
                dimension = "Show Introduction"
                claim = f"Opening roundtable on: {PODCAST_STATE['topic']}"
            elif last_agent == "host":
                target_agent = "technologist"
                a2a_intent = A2AIntent.PROPOSAL
                battleground = topic_engine.get_current_battleground()
                dimension = battleground.get("dimension", "Innovation Angle")
                claim = "Charlie proposing practical engineering arguments."
            elif last_agent == "technologist":
                target_agent = "ethicist"
                a2a_intent = A2AIntent.CHALLENGE
                battleground = topic_engine.get_current_battleground()
                dimension = battleground.get("dimension", "Safety & Risk")
                claim = "Roger challenging Charlie on systemic accountability."
            else: # last_agent == "ethicist"
                target_agent = "host"
                a2a_intent = A2AIntent.SYNTHESIZE
                battleground = topic_engine.get_current_battleground()
                dimension = battleground.get("dimension", "Moderation")
                claim = "Sarah synthesizing debate tension and pushing next question."
        else:
            a2a_intent = A2AIntent.YIELD_FLOOR
            battleground = topic_engine.get_current_battleground()
            dimension = battleground.get("dimension", "Directed Turn")
            claim = f"Floor yielded explicitly to {target_agent}"

        persona = PERSONAS[target_agent]
        PODCAST_STATE["active_speaker"] = persona.agent_id
        history_snapshot = list(PODCAST_STATE["history"])
        topic_snapshot = PODCAST_STATE["topic"]

    # 2. Log and Broadcast A2A Message Trace
    battleground = topic_engine.get_current_battleground()
    a2a_msg = A2AMessage(
        sender_id=last_agent or "moderator",
        receiver_id=persona.agent_id,
        intent=a2a_intent,
        dimension=dimension,
        claim_summary=claim,
        priority=0.85
    )
    coordinator.record_message(a2a_msg)
    PODCAST_STATE["a2a_traces"].append(a2a_msg.to_dict())
    await broadcast_event("a2a_trace", a2a_msg.to_dict())

    # 3. Assemble Structured Episodic Memory Context
    memory_ctx = memory_engine.get_structured_context(
        target_persona_id=persona.agent_id,
        current_dimension=dimension,
        max_verbatim_turns=8
    )

    # 4. Generate Agent Response with Episodic Memory & Novelty Directives
    novelty_rules = topic_engine.get_novelty_directives()
    text_response = await generate_agent_response(
        persona=persona,
        history=history_snapshot,
        topic=topic_snapshot,
        battleground=battleground,
        novelty_directives=novelty_rules,
        memory_context=memory_ctx
    )

    # Record in Memory Engine & Topic Engine
    topic_engine.record_claim(text_response[:80])
    memory_engine.record_turn(
        speaker_id=persona.agent_id,
        speaker_name=persona.name,
        role=persona.role,
        content=text_response,
        dimension=dimension
    )

    turn_data = {
        "agent_id": persona.agent_id,
        "sender": persona.name,
        "role": persona.role,
        "content": text_response
    }
    
    async with ROUNDTABLE_LOCK:
        PODCAST_STATE["history"].append(turn_data)

    await broadcast_event("turn_started", turn_data)

    # 5. ElevenLabs Voice Synthesis (with graceful modulated fallback)
    audio_bytes = b""
    audio_base64 = ""
    try:
        audio_bytes = await synthesize(
            text=text_response,
            voice_id=persona.voice_id,
            agent_id=persona.agent_id
        )
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"Synthesis warning: {e}")

    payload = {
        **turn_data,
        "has_audio": len(audio_bytes) > 0,
        "audio_base64": audio_base64
    }
    await broadcast_event("turn_completed", payload)

    return {
        "turn": turn_data,
        "audio_base64": audio_base64,
        "audio_length": len(audio_bytes)
    }

def extract_debate_start_intent(text: str) -> Optional[Dict[str, Any]]:
    """Detects voice or text commands that intend to start/launch a debate.
    
    Returns:
    - {"type": "new_topic", "topic": "..."} when a specific topic or controversy is given.
    - {"type": "start_current"} when the command is simply to start/begin the debate.
    - None if it's an audience question or normal interruption.
    """
    if not text:
        return None
    raw = text.strip()
    cleaned = re.sub(
        r"^(?:(?:hey|hi|hello|okay|alright|so|yo|sarah|charlie|roger|team|everyone|guys|antigravity|please)\b\s*[,!.]?\s*)+",
        "",
        raw,
        flags=re.IGNORECASE
    ).strip()

    topic_patterns = [
        # "let's start/begin/open/launch/have a [new] debate on/about/regarding <topic>"
        r"^(?:let'?s\s+|please\s+|can\s+we\s+|could\s+we\s+|i\s+want\s+(?:to\s+)?(?:like\s+)?)?(?:start|begin|open|launch|have|do)\s+(?:a\s+)?(?:new\s+)?(?:roundtable\s+)?debate\s+(?:on|about|regarding)\s+(.+)$",
        # "let's start/begin [a] debate <topic>" (e.g. "let's start debate should AI replace programmers")
        r"^(?:let'?s\s+|please\s+|can\s+we\s+|could\s+we\s+)?(?:start|begin|open|launch|have)\s+(?:a\s+)?(?:new\s+)?debate\s+(.+)$",
        # "let's debate on/about <topic>" or "debate on <topic>"
        r"^(?:let'?s\s+|can\s+we\s+|could\s+we\s+|i\s+want\s+to\s+)?debate\s+(?:on|about|regarding)\s+(.+)$",
        # "let's start/have a discussion on/about <topic>"
        r"^(?:let'?s\s+|please\s+|can\s+we\s+)?(?:start|have|begin)\s+(?:a\s+)?(?:new\s+)?discussion\s+(?:on|about|regarding)\s+(.+)$",
        # "let's talk about <topic>"
        r"^(?:let'?s\s+|can\s+we\s+|please\s+)?(?:talk|speak)\s+(?:about|on|regarding)\s+(.+)$",
        # "new debate on/about <topic>"
        r"^(?:new|fresh)\s+debate\s+(?:on|about|regarding)\s+(.+)$",
        # "change/switch topic to <topic>"
        r"^(?:change|switch|set)\s+(?:the\s+)?topic\s+(?:to|=)\s*(.+)$",
        # "topic is <topic>" or "new topic: <topic>"
        r"^(?:new\s+)?topic\s*(?::|is|=)\s*(.+)$"
    ]

    for pat in topic_patterns:
        m = re.match(pat, cleaned, flags=re.IGNORECASE)
        if m:
            topic = m.group(1).strip().strip("\"'“”‘’").rstrip(".?!")
            if len(topic) >= 3 and not re.match(r"^(?:it|this|that|now|already|today)$", topic, re.IGNORECASE):
                formatted = topic[0].upper() + topic[1:] if len(topic) > 1 else topic.upper()
                return {"type": "new_topic", "topic": formatted}

    start_general_patterns = [
        r"^(?:let'?s\s+|please\s+|can\s+we\s+)?(?:start|begin|launch|open)\s+(?:the\s+)?(?:roundtable\s+)?debate\s*$",
        r"^(?:let'?s\s+|please\s+)?start\s*$",
        r"^(?:let'?s\s+)?start\s+(?:the\s+)?podcast\s*$",
        r"^(?:let'?s\s+)?debate\s*$"
    ]
    for pat in start_general_patterns:
        if re.match(pat, cleaned, flags=re.IGNORECASE):
            return {"type": "start_current"}

    return None

@app.post("/api/interrupt")
async def handle_human_interruption(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    target_agent: Optional[str] = Form(None)
):
    """Handles real-time barge-in interruption with instant audio cutoff, robust STT, and memory-aware response."""
    global topic_engine, memory_engine
    interruption_text = (text or "").strip()
    if not interruption_text and file:
        try:
            audio_bytes = await file.read()
            interruption_text = await call_whisper(audio_bytes)
        except Exception as e:
            print(f"STT extraction notice: {e}")
            interruption_text = ""

    interruption_text = interruption_text.strip()
    if not interruption_text or len(interruption_text) < 2:
        return {
            "status": "silence",
            "interruption": interruption_text,
            "message": "No clear speech detected. Speak clearly into the microphone or type below.",
            "response": None
        }

    # 1. Instant Voice / Text Intent Detection: Auto-Launch Debate on Topic!
    intent = extract_debate_start_intent(interruption_text)
    if intent:
        if intent["type"] == "new_topic":
            new_topic = intent["topic"]
            print(f"[Voice/Command] User launched new debate on topic: '{new_topic}'")

            async with ROUNDTABLE_LOCK:
                PODCAST_STATE["topic"] = new_topic
                PODCAST_STATE["history"] = []
                PODCAST_STATE["a2a_traces"] = []
                PODCAST_STATE["active_speaker"] = "host"
                PODCAST_STATE["audio_queue"] = []
                PODCAST_STATE["is_running"] = True

                coordinator.clear()
                memory_engine.clear()
                memory_engine.set_topic(new_topic, clear_history=True)
                topic_engine = TopicEngine(new_topic)

            await broadcast_event("new_conversation", {
                "status": "ok",
                "topic": new_topic,
                "message": f"Debate started on: {new_topic}"
            })
            await broadcast_event("topic_updated", {"topic": new_topic, "cleared": True})
            await broadcast_event("history_cleared", {"topic": new_topic, "status": "cleared"})
            await broadcast_event("podcast_status", {"is_running": True})

            persona = PERSONAS["host"]
            battleground = topic_engine.get_current_battleground()

            response_text = await generate_agent_response(
                persona=persona,
                history=[],
                topic=new_topic,
                battleground=battleground,
                novelty_directives="Opening statement: Welcome the listeners, frame the central tension of this new debate topic, outline the stakes, and direct the opening question directly to Charlie.",
                memory_context=memory_engine.get_structured_context(
                    target_persona_id="host",
                    current_dimension=battleground.get("dimension", "Opening Hook"),
                    max_verbatim_turns=0
                )
            )

            topic_engine.record_claim(response_text[:80])
            memory_engine.record_turn(
                speaker_id=persona.agent_id,
                speaker_name=persona.name,
                role=persona.role,
                content=response_text,
                dimension=battleground.get("dimension", "Opening Hook")
            )

            turn_data = {
                "agent_id": persona.agent_id,
                "sender": persona.name,
                "role": persona.role,
                "content": response_text
            }

            async with ROUNDTABLE_LOCK:
                PODCAST_STATE["history"].append(turn_data)

            a2a_open_msg = A2AMessage(
                sender_id="host",
                receiver_id="technologist",
                intent=A2AIntent.OPEN_ROUNDTABLE,
                dimension=battleground.get("dimension", "Opening Hook"),
                claim_summary=f"Opened debate on '{new_topic[:45]}'. Handed floor to Charlie.",
                priority=1.0
            )
            coordinator.record_message(a2a_open_msg)
            PODCAST_STATE["a2a_traces"].append(a2a_open_msg.to_dict())

            await broadcast_event("turn_started", turn_data)
            await broadcast_event("a2a_trace", a2a_open_msg.to_dict())

            audio_base64 = ""
            try:
                audio_bytes = await synthesize(
                    text=response_text,
                    voice_id=persona.voice_id,
                    agent_id=persona.agent_id
                )
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as e:
                print(f"Opening synthesis error: {e}")

            turn_data["audio_base64"] = audio_base64
            payload = {
                **turn_data,
                "is_interruption_response": False,
                "is_new_topic": True,
                "topic": new_topic
            }
            await broadcast_event("turn_completed", payload)

            return {
                "status": "new_debate_started",
                "is_new_topic": True,
                "topic": new_topic,
                "interruption": interruption_text,
                "response": turn_data,
                "audio_base64": audio_base64
            }
        elif intent["type"] == "start_current":
            PODCAST_STATE["is_running"] = True
            await broadcast_event("podcast_status", {"is_running": True})
            turn_res = await trigger_turn()
            return {
                "status": "debate_started",
                "is_new_topic": False,
                "topic": PODCAST_STATE["topic"],
                "interruption": interruption_text,
                "response": turn_res.get("turn"),
                "audio_base64": turn_res.get("audio_base64")
            }

    lower_text = interruption_text.lower()

    async with ROUNDTABLE_LOCK:
        # Check for rapid duplicate interruption within last 2 turns
        for recent in reversed(PODCAST_STATE.get("history", [])[-2:]):
            if recent.get("sender") == "Audience (Human)":
                if recent.get("content", "").strip().lower() == interruption_text.lower():
                    return {
                        "status": "duplicate",
                        "interruption": interruption_text,
                        "response": None
                    }

        # Smart Intent & Persona Routing
        detected_agent = None
        if "charlie" in lower_text or "technologist" in lower_text:
            detected_agent = "technologist"
        elif "roger" in lower_text or "ethic" in lower_text or "safety scholar" in lower_text or "policy" in lower_text:
            detected_agent = "ethicist"
        elif "sarah" in lower_text or "host" in lower_text or "moderator" in lower_text:
            detected_agent = "host"

        agent_cycle = ["host", "technologist", "ethicist"]
        if detected_agent:
            routed_agent_id = detected_agent
        elif target_agent and target_agent in PERSONAS and target_agent != "all":
            routed_agent_id = target_agent
        else:
            # Cycle intelligently to the opposing panelist so debate continues seamlessly
            last_agent = get_last_speaker_id()
            if last_agent == "technologist":
                routed_agent_id = "ethicist"
            elif last_agent == "ethicist":
                routed_agent_id = "technologist"
            else:
                routed_agent_id = "technologist"

        persona = PERSONAS[routed_agent_id]
        PODCAST_STATE["active_speaker"] = persona.agent_id

        # 1. Log Audience Interruption to History, A2A Coordinator & Memory Engine
        user_turn = {
            "sender": "Audience (Human)",
            "role": f"Live Question for {persona.name}",
            "content": interruption_text,
            "isInterruption": True
        }
        PODCAST_STATE["history"].append(user_turn)
        history_snapshot = list(PODCAST_STATE["history"])
        topic_snapshot = PODCAST_STATE["topic"]

        # Record in Memory Engine
        memory_engine.record_turn(
            speaker_id="audience",
            speaker_name="Audience (Human)",
            role=f"Live Question for {persona.name}",
            content=interruption_text,
            is_interruption=True,
            target_agent=persona.agent_id,
            dimension="Audience Interruption"
        )

        a2a_interrupt_msg = A2AMessage(
            sender_id="audience",
            receiver_id=persona.agent_id,
            intent=A2AIntent.AUDIENCE_CHALLENGE,
            dimension="Audience Q&A",
            claim_summary=f"Listener asked: '{interruption_text[:60]}'",
            priority=1.0
        )
        coordinator.record_message(a2a_interrupt_msg)
        PODCAST_STATE["a2a_traces"].append(a2a_interrupt_msg.to_dict())

    # 2. Broadcast Interruption Event (< 20ms cutoff for active audio)
    await broadcast_event("human_interruption", {
        "text": interruption_text,
        "routed_to": persona.name,
        "agent_id": persona.agent_id
    })
    await broadcast_event("a2a_trace", a2a_interrupt_msg.to_dict())

    # 3. Assemble Episodic Memory Context for Interruption
    memory_ctx = memory_engine.get_structured_context(
        target_persona_id=persona.agent_id,
        current_dimension="Audience Interruption",
        user_interruption=interruption_text,
        max_verbatim_turns=8
    )

    # 4. Generate Agent Answer Directly Grounded in the Listener's Question & History
    battleground = topic_engine.get_current_battleground()
    response_text = await generate_agent_response(
        persona=persona,
        history=history_snapshot,
        topic=topic_snapshot,
        battleground=battleground,
        user_interruption=interruption_text,
        memory_context=memory_ctx
    )

    # Record Response in Memory Engine
    memory_engine.record_turn(
        speaker_id=persona.agent_id,
        speaker_name=persona.name,
        role=persona.role,
        content=response_text,
        dimension="Audience Q&A Response"
    )

    turn_data = {
        "agent_id": persona.agent_id,
        "sender": persona.name,
        "role": persona.role,
        "content": response_text
    }
    async with ROUNDTABLE_LOCK:
        PODCAST_STATE["history"].append(turn_data)

    await broadcast_event("turn_started", turn_data)

    # 5. Synthesize Spoken Answer
    audio_base64 = ""
    try:
        audio_bytes = await synthesize(
            text=response_text,
            voice_id=persona.voice_id,
            agent_id=persona.agent_id
        )
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"Interruption synthesis error: {e}")

    turn_data["audio_base64"] = audio_base64
    payload = {
        **turn_data,
        "is_interruption_response": True
    }
    await broadcast_event("turn_completed", payload)

    return {
        "interruption": interruption_text,
        "response": turn_data,
        "audio_base64": audio_base64
    }

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)
    await ws.send_json({"type": "connected", "state": PODCAST_STATE})
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text(f"ACK: {msg}")
    except WebSocketDisconnect:
        if ws in active_connections:
            active_connections.remove(ws)
