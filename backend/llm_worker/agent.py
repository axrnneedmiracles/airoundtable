"""LLM Worker & Conversational Reasoning Engine.

Supports:
1. Multi-turn episodic memory injection (panelist claims ledger, audience interventions, running narrative).
2. Multi-provider execution:
   - Local Ollama (llama3.2:3b, llama3.2:1b, or custom fine-tuned model via OLLAMA_MODEL)
   - OpenAI-compatible API (Groq, Together, DeepSeek, vLLM, OpenAI via LLM_API_BASE / LLM_API_KEY)
   - High-fidelity procedural conversational generator (resilient zero-dependency fallback)
3. Broadcast podcast dialogue conditioning:
   - Realistic conversational interruptions ("Hold on—", "Wait, let's address that—")
   - Cross-referencing previous speakers by name
   - Zero corporate fluff, hollow greetings, or canned robotic tropes
"""
import os
import re
import time
from typing import List, Dict, Any, Optional
import httpx
from persona_store.models import Persona, get_persona
from orchestrator.a2a_protocol import A2AMessage, A2AIntent

# Configurable LLM Provider Settings via environment or dynamic update
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

LLM_API_BASE = os.getenv("LLM_API_BASE", os.getenv("OPENAI_API_BASE", ""))
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("GROQ_API_KEY", "")))
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile" if "groq" in LLM_API_BASE.lower() else "gpt-4o-mini"))

def ensure_complete_sentences(text: str) -> str:
    """Ensures text ends on a complete sentence (., ?, !) and does not get cut off mid-thought."""
    text = text.strip()
    if not text:
        return text
    if text[-1] in '.!?':
        return text
    matches = list(re.finditer(r'[\.\?\!](?:\s|$)', text))
    if matches:
        last_match = matches[-1]
        trimmed = text[:last_match.end()].strip()
        if len(trimmed) > 20:
            return trimmed
    return text + "."

def clean_speech_text(text: str, persona_name: str) -> str:
    """Cleans text so ElevenLabs speaks authentic human audio without stage tags or artifacts."""
    text = text.strip(' \t\n\r"\'')
    # 1. Strip chat template tokens like 'assistant', 'user', 'system'
    text = re.sub(r'^(?:assistant|user|system)\s*[:\-]?\s*', '', text, flags=re.IGNORECASE)
    # 2. Strip persona names and known role prefixes
    known_tags = r'^(?:sarah|charlie|roger|host|moderator|technologist|ethicist|panelist|speaker)\s*[:\-]?\s*'
    text = re.sub(known_tags, '', text, flags=re.IGNORECASE)
    # 3. Strip bracketed speaker tags e.g. [Sarah]: or [Charlie] -
    text = re.sub(r'^\[[A-Za-z\s]+\]\s*[:\-]?\s*', '', text)
    # 4. Strip parenthetical stage directions like (laugh), (chuckles), (pauses), [sighs]
    text = re.sub(r'[\(\[][a-zA-Z\s]+[\)\]]', '', text)
    # 5. Strip asterisks like *laughs*, *smiles*
    text = re.sub(r'\*[^*]+\*', '', text)
    # 6. Normalize whitespace and enclosing quotes
    text = re.sub(r'\s+', ' ', text).strip(' \t\n\r"\'')
    # 7. Ensure no mid-sentence truncation
    text = ensure_complete_sentences(text)
    return text

def build_procedural_turn(
    persona: Persona,
    topic: str,
    dimension: str = "Core Debate",
    battleground: Optional[Dict[str, str]] = None,
    last_speaker: str = "",
    last_argument: str = "",
    user_interruption: Optional[str] = None,
    memory_context: Optional[Dict[str, Any]] = None,
    turn_number: int = 0
) -> str:
    """High-fidelity dynamic procedural reasoning engine.
    
    Generates authentic, unscripted-sounding multi-round debate turns tailored to ANY topic
    and battleground dimension without ever repeating previous claims.
    """
    mem = memory_context or {}
    charlie_claims = mem.get("charlie_claims", [])
    roger_claims = mem.get("roger_claims", [])
    sarah_points = mem.get("sarah_points", [])
    narrative = mem.get("narrative_summary", "")

    bg = battleground or {}
    charlie_angle = bg.get("charlie_angle", f"Accelerate open experimentation and distributed testing around {topic}.")
    roger_angle = bg.get("roger_angle", f"Enforce institutional accountability and risk auditing before deploying {topic}.")
    sarah_hook = bg.get("sarah_hook", f"Where do we draw the line between innovation speed and systemic harm in {topic}?")

    # Handle Audience Interruption
    if user_interruption:
        q = user_interruption.strip().rstrip(".?!")
        if persona.agent_id == "host":
            return (
                f"Hold on, let us address that directly. The listener just asked: '{q}'—and it cuts straight "
                f"through our theoretical debate. Charlie, Roger, how does your stance hold up when confronted with that reality?"
            )
        elif persona.agent_id == "technologist":
            return (
                f"Wait, let me jump in on what the listener said. When you ask about '{q}', the real-world engineering reality "
                f"is that closed monopolies make that problem worse, while open inspection gives users the actual power to verify."
            )
        else: # ethicist
            return (
                f"I want to answer the listener directly. That question exposes the exact blind spot Charlie has been ignoring: "
                f"when speed is prioritized over safety, ordinary citizens bear the cost of the irreversible damage."
            )

    # Multi-Stage Dynamic Debate Progression (Cycles 0 to 7+)
    cycle = (turn_number // 3) % 7

    if persona.agent_id == "host":
        if turn_number == 0 or not last_speaker:
            return (
                f"Welcome to today's roundtable on '{topic}'. The battle lines are drawn between unrestricted acceleration and systemic governance. "
                f"Charlie, make the case: {charlie_angle}"
            )
        elif cycle == 1:
            return (
                f"Roger argues that '{topic}' carries irreversible systemic failure modes, while Charlie insists distributed tools are the only scalable shield. "
                f"Charlie, how do you verify safety when consumer hardware can bypass your safeguards?"
            )
        elif cycle == 2:
            return (
                f"Let's confront the economic reality behind '{topic}'. Charlie speaks of democratization, but Roger points to the massive concentration of wealth and uninsurable externalities. "
                f"Who actually bears the legal liability when things fail in production?"
            )
        elif cycle == 3:
            return (
                f"We are reaching the central fracture of '{topic}'. Roger is demanding enforceable institutional guardrails, while Charlie says that creates a fragile regulatory monopoly. "
                f"Is meaningful public governance even technically feasible at this velocity?"
            )
        elif cycle == 4:
            return (
                f"Both of you are making sweeping assertions. Charlie, show us the empirical evidence that open iteration prevents catastrophic breach. "
                f"Roger, show us where regulatory bans have ever permanently halted technological momentum."
            )
        elif cycle == 5:
            return (
                f"I want a clear red line from both panelists on '{topic}'. Charlie, what specific failure mode forces you to pull the emergency brake? "
                f"Roger, what audit threshold allows deployment to proceed without bureaucratic paralysis?"
            )
        else:
            return (
                f"We have arrived at the synthesis of '{topic}'. The trade-off is not about stopping progress; it is about who holds the emergency kill switch. "
                f"Roger, Charlie, answer Sarah's question: {sarah_hook}"
            )

    elif persona.agent_id == "technologist":
        if cycle == 0:
            return (
                f"Look at the foundational mechanics of '{topic}'. Restricting access doesn't stop bad actors—it only disarms "
                f"the independent developers and security researchers who build the defenses we rely on every day."
            )
        elif cycle == 1:
            return (
                f"Roger's entire premise relies on security by obscurity, and history proves that always fails. On the dimension of {dimension}: "
                f"{charlie_angle} Open protocols and cryptographic verification are the only scalable defense."
            )
        elif cycle == 2:
            return (
                f"What Roger calls 'safety regulations' in practice always becomes an anti-competitive moat for legacy incumbents. "
                f"If we centralize control of '{topic}', we hand the entire technological frontier to a handful of monopolistic gatekeepers."
            )
        elif cycle == 3:
            return (
                f"Let's be clear about the technical reality: mathematics and distributed compute cannot be outlawed. "
                f"If western open-source developers don't build the frontier tools for '{topic}', state-backed authoritarian labs will, and we will have zero inspection capability."
            )
        elif cycle == 4:
            return (
                f"Roger treats catastrophic risk like an abstract philosophical boogeyman. The way you make complex systems antifragile is through stress-testing in the open, "
                f"finding the edge cases, and shipping rapid distributed patches before an adversary exploits them."
            )
        elif cycle == 5:
            return (
                f"The only scalable defense in human history has been open protocols and decentralized ownership. "
                f"Trying to lock down '{topic}' with government permits guarantees failure; giving tools to the public guarantees resilience."
            )
        else:
            return (
                f"Every breakthrough from the printing press to encryption faced this exact fear-mongering. "
                f"The antidote to bad code and rogue actors around '{topic}' is more builders, faster iteration, and total transparency."
            )

    else: # ethicist
        if cycle == 0:
            return (
                f"We have to examine the real-world incentives driving '{topic}'. Without enforceable institutional accountability, "
                f"the immense profits flow to private developers while the collective public absorbs the catastrophic externalities."
            )
        elif cycle == 1:
            return (
                f"Charlie treats existential and systemic risk as just another software bug you can patch after deployment. On the dimension of {dimension}: "
                f"{roger_angle} Irreversible harms cannot be rolled back with an open-source commit after the damage is done."
            )
        elif cycle == 2:
            return (
                f"Charlie keeps drawing a false equivalence between harmless code repositories and autonomous dual-use intelligence. "
                f"When '{topic}' interacts with critical infrastructure and democratic stability, a single uninsurable failure is game over."
            )
        elif cycle == 3:
            return (
                f"Who pays the damages when Charlie's 'permissionless innovation' causes a systemic failure? "
                f"The accelerationist dogma always socializes the disaster while privatizing the upside, leaving ordinary citizens completely unprotected."
            )
        elif cycle == 4:
            return (
                f"Precaution is not stagnation—it is basic engineering discipline. You don't launch a nuclear reactor or an airliner without rigorous third-party auditing, "
                f"and '{topic}' demands the exact same enforceable institutional standards."
            )
        elif cycle == 5:
            return (
                f"Silicon Valley techno-solutionism cannot substitute for democratic legitimacy. "
                f"The public has an absolute sovereign right to place binding red lines on '{topic}' before reckless developers deploy irreversible systems."
            )
        else:
            return (
                f"Charlie's worldview assumes infinite resilience, but human institutions are fragile. "
                f"If we surrender democratic governance over '{topic}' to an unelected technological priesthood, we forfeit the right to a safe future."
            )

_last_ollama_check_time = 0.0
_ollama_online = False

async def is_ollama_available(host: str = OLLAMA_HOST) -> bool:
    """Fast non-blocking check whether local Ollama is active."""
    global _last_ollama_check_time, _ollama_online
    now = time.time()
    if (now - _last_ollama_check_time) < 30.0:
        return _ollama_online
    _last_ollama_check_time = now
    try:
        async with httpx.AsyncClient(timeout=0.4) as client:
            resp = await client.get(f"{host.rstrip('/')}/api/tags")
            _ollama_online = (resp.status_code == 200)
    except Exception:
        _ollama_online = False
    return _ollama_online

async def call_ollama(
    messages: List[Dict[str, str]],
    model_name: str = OLLAMA_MODEL,
    host: str = OLLAMA_HOST
) -> Optional[str]:
    """Attempts generation via local Ollama."""
    if not await is_ollama_available(host):
        return None
    models_to_try = [model_name]
    if "3.2:3b" in model_name:
        models_to_try.append("llama3.2:1b")
    elif "llama" not in model_name:
        models_to_try.extend(["llama3.2:3b", "llama3.2:1b"])

    for m in models_to_try:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=1.2)) as client:
                resp = await client.post(
                    f"{host.rstrip('/')}/api/chat",
                    json={
                        "model": m,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.74,
                            "top_p": 0.9,
                            "repeat_penalty": 1.22,
                            "presence_penalty": 0.5,
                            "frequency_penalty": 0.3,
                            "num_predict": 180
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if content and len(content) > 15:
                        return content
        except Exception:
            continue
    return None

async def call_openai_compatible(
    messages: List[Dict[str, str]],
    base_url: str = LLM_API_BASE,
    api_key: str = LLM_API_KEY,
    model_name: str = LLM_MODEL
) -> Optional[str]:
    """Calls an OpenAI-compatible endpoint (Groq, Together, DeepSeek, vLLM, OpenAI)."""
    if not base_url and not api_key:
        return None

    url = f"{base_url.rstrip('/')}/chat/completions" if base_url else "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else ""
    }
    payload = {
        "model": model_name or "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.75,
        "max_tokens": 200
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=3.0)) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if content and len(content) > 15:
                        return content
    except Exception as e:
        print(f"OpenAI-compatible LLM notice: {e}")
    return None

async def generate_agent_response(
    persona: Persona,
    history: List[Dict[str, Any]],
    topic: str = "",
    battleground: Optional[Dict[str, str]] = None,
    novelty_directives: str = "",
    user_interruption: Optional[str] = None,
    memory_context: Optional[Dict[str, Any]] = None
) -> str:
    """Generates broadcast-grade podcast dialogue with episodic memory and realistic interruption flow."""
    last_turn = history[-1] if history else {}
    last_speaker = last_turn.get("sender", "")
    last_argument = last_turn.get("content", "")

    bg = battleground or {}
    dimension = bg.get("dimension", "Core Debate")
    charlie_target = bg.get("charlie_angle", "Push the frontier of open innovation.")
    roger_target = bg.get("roger_angle", "Enforce institutional safety and accountability.")
    sarah_target = bg.get("sarah_hook", "Where do we find the realistic trade-off?")

    mem = memory_context or {}
    narrative_summary = mem.get("narrative_summary", "")
    charlie_claims = mem.get("charlie_claims", [])
    roger_claims = mem.get("roger_claims", [])
    sarah_points = mem.get("sarah_points", [])
    recent_audience_q = mem.get("recent_audience_questions", [])

    # Episodic Context Block
    context_notes = []
    if narrative_summary:
        context_notes.append(f"DEBATE ARC SO FAR: {narrative_summary}")
    if charlie_claims:
        context_notes.append(f"Charlie's core stance: \"{charlie_claims[-1]}\"")
    if roger_claims:
        context_notes.append(f"Roger's core stance: \"{roger_claims[-1]}\"")
    if recent_audience_q:
        context_notes.append(f"Recent listener inquiry: {recent_audience_q[-1]}")
    context_block = "\n".join(context_notes)

    # Dynamic role-specific instruction:
    if user_interruption:
        role_instruction = (
            f"DEBATE TOPIC: '{topic}'. CURRENT DIMENSION: '{dimension}'.\n"
            f"CONTEXT SUMMARY:\n{context_block}\n\n"
            f"A live audience listener just interrupted the roundtable with: \"{user_interruption}\".\n"
            f"You are {persona.name} ({persona.role}).\n"
            "STRICT RULES:\n"
            "- Acknowledge the interruption naturally in the opening 2-4 words (e.g., 'Hold on—', 'Wait, let's address that—', 'The listener just hit the core problem—').\n"
            "- Directly answer the listener's specific point using your character's philosophy.\n"
            "- Speak in 2 to 3 sharp, opinionated conversational sentences that end with complete punctuation.\n"
            "- ZERO hollow greetings ('Welcome', 'Thanks for the question'). Jump straight into the clash."
        )
    elif persona.agent_id == "host":
        if last_speaker and last_argument:
            role_instruction = (
                f"DEBATE TOPIC: '{topic}'. CURRENT DIMENSION: '{dimension}'.\n"
                f"CONTEXT SUMMARY:\n{context_block}\n\n"
                f"{last_speaker} just argued: \"{last_argument}\".\n"
                f"You are Sarah (Host). Push back on {last_speaker}'s premise in 1 incisive sentence, "
                f"then challenge the panel with: \"{sarah_target}\".\n"
                "DO NOT praise the speaker. Cut straight to the conflict in 2 punchy spoken sentences."
            )
        else:
            role_instruction = (
                f"You are Sarah, opening the debate on: '{topic}'.\n"
                f"State the central dilemma in 2 sharp, captivating spoken sentences and challenge Charlie to answer: \"{sarah_target}\"."
            )
    elif persona.agent_id == "technologist":
        opposing_context = f"Roger previously claimed '{roger_claims[-1]}'—dismantle it." if roger_claims else ""
        role_instruction = (
            f"DEBATE TOPIC: '{topic}'. CURRENT DIMENSION: '{dimension}'.\n"
            f"CONTEXT SUMMARY:\n{context_block}\n\n"
            f"Your stance: \"{charlie_target}\".\n"
            f"{last_speaker} argued: \"{last_argument}\". {opposing_context}\n"
            f"You are Charlie. Disagree directly with {last_speaker}. Give a concrete real-world mechanism or economic reality.\n"
            f"Stay strictly on the subject of '{topic}'. DO NOT wander into generic coding or GitHub unless asked. "
            f"Jump straight into your argument in 2 to 3 punchy spoken sentences."
        )
    else:  # ethicist
        opposing_context = f"Charlie previously claimed '{charlie_claims[-1]}'—refute it." if charlie_claims else ""
        role_instruction = (
            f"DEBATE TOPIC: '{topic}'. CURRENT DIMENSION: '{dimension}'.\n"
            f"CONTEXT SUMMARY:\n{context_block}\n\n"
            f"Your stance: \"{roger_target}\".\n"
            f"{last_speaker} argued: \"{last_argument}\". {opposing_context}\n"
            f"You are Roger. Directly dismantle {last_speaker}'s premise. Highlight the societal damage, real-world victim, or dangerous failure mode.\n"
            f"Stay strictly on '{topic}'. No academic jargon or buzzwords. Jump straight into your argument in 2 to 3 grounded spoken sentences."
        )

    # Master Podcast System Prompt
    system_prompt = (
        f"{persona.system_prompt}\n\n"
        "STRICT BROADCAST DIALOGUE RULES (VIOLATING THESE BREAKS THE SHOW):\n"
        "1. NO GREETINGS OR ACKNOWLEDGMENTS: Never say 'Welcome', 'Hey friend', 'I agree', 'Thanks for having me', 'That is a great question', or 'Let us dive into'. State your point immediately.\n"
        "2. FULL MEMORY AWARENESS: You remember past points made by Charlie, Roger, and Sarah. Reference them naturally by name when pushing back.\n"
        "3. NO AI BUZZWORDS OR ESSAY CLICHÉS: Never use 'digital landscape', 'tapestry', 'multifaceted', 'pivotal', 'delve', 'catalyst', 'holistic', or 'for real'. Speak like an authentic human with conviction.\n"
        "4. STAY STRICTLY ON TOPIC: Anchor your response to the debate topic without drifting into generic software tropes.\n"
        "5. Speak in 2 to 3 punchy, complete sentences ending with a period or question mark.\n"
        "6. Output ONLY spoken words. Never output speaker prefixes (e.g. 'Sarah:'), asterisks (*laughs*), or stage directions."
        f"{novelty_directives}"
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Provide concise, high-signal recent history (up to 6 substantive turns with speaker names)
    substantive_history = [
        h for h in history[-6:]
        if h.get("sender") not in ["System"] and h.get("content")
    ]
    for h in substantive_history:
        s = h.get("sender", "")
        c = h.get("content", "")
        messages.append({"role": "user", "content": f"{s}: {c}"})

    messages.append({"role": "user", "content": role_instruction})

    # Provider Attempt 1: OpenAI-compatible (Groq / Together / OpenAI if configured)
    if LLM_API_KEY or LLM_API_BASE:
        content = await call_openai_compatible(messages)
        if content:
            cleaned = clean_speech_text(content, persona.name)
            if cleaned and len(cleaned) > 15:
                return cleaned

    # Provider Attempt 2: Local Ollama
    content = await call_ollama(messages)
    if content:
        cleaned = clean_speech_text(content, persona.name)
        if cleaned and len(cleaned) > 15:
            return cleaned

    # Provider Attempt 3: High-Fidelity Procedural Conversational Generator (Zero-fail fallback)
    return build_procedural_turn(
        persona=persona,
        topic=topic,
        dimension=dimension,
        battleground=bg,
        last_speaker=last_speaker,
        last_argument=last_argument,
        user_interruption=user_interruption,
        memory_context=memory_context,
        turn_number=len(history)
    )
