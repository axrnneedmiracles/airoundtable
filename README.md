# 🎙️ AI Roundtable: Real-Time Multi-Agent Voice Podcast
> **ElevenLabs Track — FOSS Forge 2.0 Hackathon**  
> An autonomous, voice-native roundtable podcast featuring distinct AI personas debating high-stakes ideas in real time, with instant human barge-in interruption and live Agent-to-Agent (A2A) protocol traces.

---

## ⚡ Highlights & Key Features

- **🗣️ Voice-Native Layer (ElevenLabs Flash v2.5)**: Low-latency, emotionally expressive speech generation featuring tailored voice profiles:
  - **Sarah** (*Host & Synthesizer* — Voice: `Rachel`)
  - **Charlie** (*AI Accelerationist Hacker* — Voice: `Charlie`)
  - **Roger** (*AI Safety & Governance Scholar* — Voice: `Roger`)
- **🛑 Real-Time Barge-In Interruption (< 20ms)**: Speak at any moment to cut off talking agents. Built-in Hands-Free Auto-VAD (Voice Activity Detection) and room noise filtering.
- **🎙️ Dual-Engine STT Pipeline**:
  - *Primary*: Browser Web Speech API for instantaneous, zero-lag live speech preview as you talk.
  - *Secondary*: Local Apple Metal GPU accelerated `whisper.cpp` (`ggml-small.en-q5_1.bin`) with Silero VAD for high-accuracy phonetic transcription.
- **🤝 Agent-to-Agent (A2A) Coordination Protocol**: Structured turn deliberation bus (`CHALLENGE`, `PROPOSAL`, `SYNTHESIZE`, `AUDIENCE_CHALLENGE`) rendered live in the telemetry stream.
- **🧠 Zero-Fluff Persona Prompting**: Substantive, opinionated debate arguments without hollow greetings, corporate filler, or robotic buzzwords.
- **🌐 Glassmorphic Studio Dashboard**: Sleek dark UI, responsive multi-column layout, dynamic voice orb visualizer, and curated one-click topic presets.

---

## 🏗️ Architecture

```
                               ┌────────────────────────────────┐
                               │  Browser Frontend (HTML5/CSS3) │
                               │   - Interactive Audio Visualizer│
                               │   - Live A2A Protocol Stream   │
                               │   - Hands-Free Auto-VAD Engine │
                               └──────────────┬─────────────────┘
                                              │ WebSocket / HTTP
                                              ▼
                               ┌────────────────────────────────┐
                               │ FastAPI Orchestrator (Port 8000)│
                               │   - State & Session Manager    │
                               │   - Turn Arbiter & Topic Engine│
                               │   - A2A Deliberation Bus       │
                               └───────┬──────────────┬─────────┘
                                       │              │
                    ┌──────────────────┘              └──────────────────┐
                    ▼                                                    ▼
       ┌────────────────────────┐                           ┌────────────────────────┐
       │   Local Ollama Engine  │                           │ ElevenLabs Flash v2.5  │
       │     (Llama 3.2 3B)     │                           │  High-Fidelity Audio   │
       │   - Persona System     │                           │   Synthesis (TTS)      │
       │   - Debate Novelty     │                           └────────────────────────┘
       └────────────────────────┘                                        ▲
                    │                                                    │
                    ▼                                                    │
       ┌────────────────────────┐                                        │
       │ whisper.cpp + Metal GPU│                                        │
       │   - Local 244M Small   │────────────────────────────────────────┘
       │   - Silero VAD Filter  │
       └────────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.12 / 3.14)
- **Ollama** installed locally (`brew install ollama` or [ollama.ai](https://ollama.ai))
  ```bash
  ollama pull llama3.2:3b
  ollama serve
  ```
- **FFmpeg** (`brew install ffmpeg`)
- **ElevenLabs API Key** ([elevenlabs.io](https://elevenlabs.io))

### 2. Environment Configuration
Clone the repository and copy the example environment file:
```bash
git clone https://github.com/piyush588/Multi_agent_podcast.git
cd Multi_agent_podcast

cp .env.example .env
# Edit .env and paste your ELEVENLABS_API_KEY
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Local whisper.cpp STT Server
To run local Metal GPU accelerated speech-to-text:
```bash
git clone https://github.com/ggerganov/whisper.cpp.git backend/whisper_cpp
cd backend/whisper_cpp
cmake -B build -DWHISPER_METAL=ON
cmake --build build --config Release -j
bash ./models/download-ggml-model.sh small.en-q5_1
./build/bin/whisper-server --host 0.0.0.0 --port 8080 -m models/ggml-small.en-q5_1.bin --vad -vt 0.50
```

### 5. Launch the Studio Server
From the root directory:
```bash
python -m uvicorn backend.orchestrator.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser to:
```
http://localhost:8000
```

---

## 🎮 How to Interact

1. **Start Autonomous Roundtable**: Click the main toggle to launch the live debate.
2. **Select Curated Topics**: Switch between *Urban Infrastructure*, *The Post-Labor Economy*, *Neural Augmentation*, *Powering Planetary AGI*, or *Information Warfare*.
3. **Interrupt Anytime**:
   - **Voice**: Speak into your microphone. The AI speaker immediately pauses (< 20ms) and listens.
   - **Text**: Type a rebuttal in the interruption input and press Enter.
   - **Direct Address**: Click on any panelist (Sarah, Charlie, Roger) to route your question directly to them.

---

## 📜 License
MIT License. Built for the ElevenLabs Track at FOSS Forge 2.0.
