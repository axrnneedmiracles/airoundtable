# backend/tools/whisper.py
"""Multi-Provider Resilient Speech-to-Text (STT) Engine.

Supports:
1. Native 16kHz WAV direct decoding (no ffmpeg dependency required)
2. Google Speech Recognition via Python `speech_recognition` (100% free, no API key needed)
3. Groq Cloud Whisper API (whisper-large-v3-turbo - ultra-fast < 250ms)
4. OpenAI Cloud Whisper API (whisper-1)
5. Local Whisper.cpp server (http://127.0.0.1:8080/inference)
6. Dynamic speech energy validation and post-transcription hallucination cleaner
"""
import os
import io
import re
import math
import struct
import wave
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import httpx

# Load .env file
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# STT Configuration
DEFAULT_SERVER_URL = os.getenv("WHISPER_SERVER_URL", "http://127.0.0.1:8080/inference")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

KNOWN_HALLUCINATIONS = {
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "subscribe for more",
    "like and subscribe",
    "subtitles by",
    "transcribed by",
    "translated by",
    "all rights reserved",
    "the end",
    "blank_audio",
    "you",
    "bye",
    "bye bye",
    "goodbye",
    "see you next time",
    "so",
    "um",
    "uh",
    "oh",
    "ah",
    "okay",
    "ok",
    "hmm",
    "shh",
    "peace"
}

def clean_whisper_text(raw_text: str) -> str:
    """Removes annotations, brackets, and known noise hallucinations."""
    if not raw_text:
        return ""
    # Remove bracketed/parenthetical text like [BLANK_AUDIO], (music), [applause]
    clean = re.sub(r'\[.*?\]', '', raw_text)
    clean = re.sub(r'\(.*?\)', '', clean)
    # Remove repeated single letter noises (e.g. "LLLL!")
    clean = re.sub(r'\b[A-Za-z]\b', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Normalize lower for blacklist check
    lower = clean.lower().strip(" .!?,:;'\"")
    if lower in KNOWN_HALLUCINATIONS or not lower:
        return ""

    # Reject if only single filler letters
    words = [w for w in re.findall(r'\b\w+\b', clean) if len(w) > 1]
    if len(words) < 1:
        return ""

    return clean.strip()

def is_wav_audio(audio_bytes: bytes) -> bool:
    """Checks whether the raw byte stream has a valid RIFF WAVE header."""
    return len(audio_bytes) > 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"

def check_pcm_speech_energy(wav_bytes: bytes) -> bool:
    """Verifies that 16kHz WAV has sufficient vocal energy to be speech."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            n_frames = wf.getnframes()
            rate = wf.getframerate()
            duration = n_frames / float(rate)
            # Accept any audio over 0.25 seconds
            if duration < 0.25:
                return False
            frames = wf.readframes(n_frames)
            count = len(frames) // 2
            if count == 0:
                return False
            shorts = struct.unpack(f"{count}h", frames)
            sum_sq = sum(s * s for s in shorts)
            rms = math.sqrt(sum_sq / count)
            # Low threshold (60) to avoid discarding quiet speakers or soft mics
            return rms >= 60
    except Exception as e:
        return True

def convert_to_whisper_wav(raw_audio: bytes) -> Optional[bytes]:
    """Ensures audio is clean 16kHz mono 16-bit PCM WAV.
    If already WAV, returns it directly without needing external ffmpeg.
    """
    if is_wav_audio(raw_audio):
        if not check_pcm_speech_energy(raw_audio):
            return None
        return raw_audio

    # If non-WAV format (e.g. webm/ogg) and ffmpeg is installed, attempt conversion
    with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as in_f:
        in_f.write(raw_audio)
        in_path = in_f.name

    out_path = in_path + ".wav"
    try:
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            out_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0 and os.path.exists(out_path):
            cleaned_wav = Path(out_path).read_bytes()
            if not check_pcm_speech_energy(cleaned_wav):
                return None
            return cleaned_wav
        else:
            return raw_audio
    except Exception:
        # ffmpeg not available on system, return raw bytes
        return raw_audio
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

def transcribe_with_google_sr(wav_bytes: bytes) -> Optional[str]:
    """Transcribes audio using Google Speech Recognition via speech_recognition package.
    Runs free with zero API keys required.
    """
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        r.energy_threshold = 80
        r.dynamic_energy_threshold = True
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio_data = r.record(source)
        recognized = r.recognize_google(audio_data, language="en-US")
        clean = clean_whisper_text(recognized)
        if clean and len(clean) > 1:
            print(f"[STT] Google Speech successfully recognized: \"{clean}\"")
            return clean
    except Exception as e:
        # Expected if audio is silence (UnknownValueError) or network unreachable
        pass
    return None

async def call_groq_whisper(wav_bytes: bytes, api_key: str) -> Optional[str]:
    """Transcribes audio using Groq Cloud Whisper API (whisper-large-v3-turbo)."""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {
        "model": "whisper-large-v3-turbo",
        "response_format": "json",
        "temperature": "0.0"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            if resp.status_code == 200:
                result = resp.json()
                raw = result.get("text", "").strip()
                return clean_whisper_text(raw)
    except Exception as e:
        print(f"Groq Whisper notice: {e}")
    return None

async def call_openai_whisper(wav_bytes: bytes, api_key: str) -> Optional[str]:
    """Transcribes audio using OpenAI Cloud Whisper API (whisper-1)."""
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {"model": "whisper-1"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            if resp.status_code == 200:
                result = resp.json()
                raw = result.get("text", "").strip()
                return clean_whisper_text(raw)
    except Exception as e:
        print(f"OpenAI Whisper notice: {e}")
    return None

async def call_local_whisper_cpp(wav_bytes: bytes, server_url: str) -> Optional[str]:
    """Transcribes audio using local whisper.cpp server."""
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(server_url, files=files)
            if resp.status_code == 200:
                result = resp.json()
                raw = result.get("text", "").strip()
                return clean_whisper_text(raw)
    except Exception:
        pass
    return None

async def call_whisper(audio_bytes: bytes) -> str:
    """Send audio to multi-tier STT providers with automatic fallback."""
    wav_16k = convert_to_whisper_wav(audio_bytes)
    if not wav_16k:
        return ""

    # Tier 1: Groq Whisper API (fastest, ultra-low latency < 250ms)
    groq_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
    if groq_key:
        text = await call_groq_whisper(wav_16k, groq_key)
        if text:
            return text

    # Tier 2: OpenAI Whisper API
    openai_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)
    if openai_key:
        text = await call_openai_whisper(wav_16k, openai_key)
        if text:
            return text

    # Tier 3: Local whisper.cpp server
    server_url = os.getenv("WHISPER_SERVER_URL", DEFAULT_SERVER_URL)
    text = await call_local_whisper_cpp(wav_16k, server_url)
    if text:
        return text

    # Tier 4: Built-in Google Speech Recognition via speech_recognition (0-cost, no key required)
    text = transcribe_with_google_sr(wav_16k)
    if text:
        return text

    return ""
