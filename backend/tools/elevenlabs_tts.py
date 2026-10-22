"""ElevenLabs Studio Voice Synthesis Engine.

Supports:
1. ElevenLabs Flash v2.5 low-latency neural TTS.
2. Dynamic API key configuration at runtime via /api/config/tts.
3. Persona-specific voice IDs (Sarah, Charlie, Roger).
4. Procedural fallback audio wave generation when API key is not yet set,
   ensuring the visualizer particle sphere, telemetry spectrum, and turn timers
   function flawlessly with zero crashes.
"""
import os
import io
import math
import struct
import wave
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv, set_key
import httpx

# Load .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Default Studio Voices for Personas:
# Sarah: "Rachel / Sarah" (EXAVITQu4vr4xnSDxMaL)
# Charlie: "Charlie" (IKne3meq5aSn9XLyUdCD)
# Roger: "Roger" (CwhRBWXzGAHq8TQ4Fs17)
PERSONA_VOICES: Dict[str, str] = {
    "host": "EXAVITQu4vr4xnSDxMaL",
    "technologist": "IKne3meq5aSn9XLyUdCD",
    "ethicist": "CwhRBWXzGAHq8TQ4Fs17"
}

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

def set_elevenlabs_api_key(new_key: str, persist_to_env: bool = True) -> bool:
    """Updates ElevenLabs API key dynamically in memory and optionally writes to .env."""
    global ELEVENLABS_API_KEY
    clean_key = new_key.strip()
    ELEVENLABS_API_KEY = clean_key
    os.environ["ELEVENLABS_API_KEY"] = clean_key

    if persist_to_env:
        try:
            if not env_path.exists():
                env_path.write_text(f"ELEVENLABS_API_KEY={clean_key}\n", encoding="utf-8")
            else:
                set_key(str(env_path), "ELEVENLABS_API_KEY", clean_key)
        except Exception as e:
            print(f"Notice persisting key to .env: {e}")
    return True

def get_tts_status() -> Dict[str, Any]:
    """Returns current TTS configuration status."""
    active_key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)
    is_set = bool(active_key and len(active_key) > 8 and not active_key.startswith("your_"))
    masked = f"{active_key[:6]}...{active_key[-4:]}" if is_set else "Not Configured"
    return {
        "is_configured": is_set,
        "masked_key": masked,
        "model_id": "eleven_flash_v2_5",
        "voices": PERSONA_VOICES
    }

def generate_fallback_audio_wav(text: str, voice_type: str = "host") -> bytes:
    """Generates a pleasant modulated harmonic PCM WAV audio track.
    
    Ensures that when ElevenLabs API key is not yet provided, the frontend
    audio visualizer orb, waveform bars, and turn timers still receive real audio
    frequencies to analyze and react to in real time.
    """
    word_count = max(1, len(text.split()))
    # Natural speaking rate: ~2.8 words per second
    duration = min(8.0, max(1.8, word_count / 2.8))
    sample_rate = 22050
    total_samples = int(sample_rate * duration)

    # Base frequencies per persona
    pitch_map = {
        "host": 260.0,         # Sarah (soprano/alto moderator)
        "technologist": 190.0, # Charlie (tenor systems engineer)
        "ethicist": 140.0      # Roger (baritone policy scholar)
    }
    base_freq = pitch_map.get(voice_type, 220.0)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = float(i) / sample_rate
            # Dynamic cadence modulation simulating speech syllables (~4 syllables per second)
            envelope = (math.sin(t * math.pi * 7.5) * 0.35 + 0.65)
            # Attack and decay ramps
            if t < 0.15:
                envelope *= (t / 0.15)
            elif t > (duration - 0.25):
                envelope *= max(0.0, (duration - t) / 0.25)

            # Harmonic vocal formant mix (fundamental + harmonics)
            wave1 = math.sin(2.0 * math.pi * base_freq * t)
            wave2 = 0.5 * math.sin(2.0 * math.pi * (base_freq * 1.5) * t)
            wave3 = 0.25 * math.sin(2.0 * math.pi * (base_freq * 2.0) * t)
            sample_val = int((wave1 + wave2 + wave3) * envelope * 8000.0)
            sample_val = max(-32767, min(32767, sample_val))
            frames.extend(struct.pack("<h", sample_val))

        wf.writeframes(frames)

    return buf.getvalue()

async def synthesize(text: str, voice_id: str = DEFAULT_VOICE_ID, agent_id: str = "host") -> bytes:
    """Synthesize speech using ElevenLabs API. Falls back to synthetic modulated audio if key not set."""
    api_key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY).strip()

    # If key is missing or placeholder, generate harmonic fallback audio
    if not api_key or api_key.startswith("your_"):
        return generate_fallback_audio_wav(text, voice_type=agent_id)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                print(f"ElevenLabs API warning ({response.status_code}): {response.text[:120]}")
    except Exception as e:
        print(f"ElevenLabs network exception: {e}")

    # Fallback if request fails
    return generate_fallback_audio_wav(text, voice_type=agent_id)
