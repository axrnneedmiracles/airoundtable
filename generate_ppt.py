"""Generate Professional 6-Slide PowerPoint Presentation for AI Roundtable with Embedded UI Screenshots.
File: ppt_airoundtable.pptx
"""
import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Palette (Sleek Studio Dark Theme with ElevenLabs Warm Accents)
    COLOR_BG = RGBColor(16, 18, 24)             # Deep Obsidian (#101218)
    COLOR_CARD = RGBColor(24, 28, 38)           # Surface Card (#181C26)
    COLOR_CARD_BORDER = RGBColor(42, 48, 64)    # Subtle Border (#2A3040)
    COLOR_WHITE = RGBColor(255, 255, 255)       # Pure White (#FFFFFF)
    COLOR_TEXT_MUTED = RGBColor(156, 163, 175)  # Muted Gray (#9CA3AF)
    COLOR_ORANGE = RGBColor(255, 107, 74)       # ElevenLabs Terracotta (#FF6B4A)
    COLOR_AMBER = RGBColor(245, 158, 11)        # Warm Amber (#F59E0B)
    COLOR_PURPLE = RGBColor(139, 92, 246)       # Host Purple (#8B5CF6)
    COLOR_BLUE = RGBColor(59, 130, 246)         # Tech Blue (#3B82F6)
    COLOR_EMERALD = RGBColor(16, 185, 129)      # Ethic Emerald (#10B981)

    # Screenshot Paths (Local Workspace)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SS_DIR = os.path.join(BASE_DIR, "screenshots")
    SS_MAIN = os.path.join(SS_DIR, "main_page_1792647616993.png")
    SS_BURST = os.path.join(SS_DIR, "talking_state_burst_1792630695192.png")
    SS_MEMORY = os.path.join(SS_DIR, "memory_modal_1792647640036.png")
    SS_SETTINGS = os.path.join(SS_DIR, "settings_modal_1792647624563.png")

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.fill.background()
        return bg

    def add_card(slide, left, top, width, height, fill_color=COLOR_CARD, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = fill_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    def add_image_card(slide, left, top, width, height, img_path, title_text, accent_color, bullets=None):
        """Creates a framed presentation showcase card with an embedded UI screenshot."""
        card = add_card(slide, left, top, width, height)
        
        # Top color accent bar
        cbar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(0.08))
        cbar.fill.solid()
        cbar.fill.fore_color.rgb = accent_color
        cbar.line.fill.background()

        # Header Title
        tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.12), width - Inches(0.4), Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"●  {title_text}"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = accent_color
        p.font.name = "Segoe UI"

        # Embedded Screenshot
        img_top = top + Inches(0.55)
        img_left = left + Inches(0.2)
        img_width = width - Inches(0.4)
        
        if os.path.exists(img_path):
            pic = slide.shapes.add_picture(img_path, img_left, img_top, width=img_width)
            actual_img_bottom = img_top + pic.height
        else:
            actual_img_bottom = img_top + Inches(2.2)

        # Bullets / Caption below the image
        if bullets:
            cap_tb = slide.shapes.add_textbox(
                left + Inches(0.2), 
                actual_img_bottom + Inches(0.12), 
                width - Inches(0.4), 
                height - (actual_img_bottom - top) - Inches(0.2)
            )
            cap_tf = cap_tb.text_frame
            cap_tf.word_wrap = True
            for b_idx, b in enumerate(bullets):
                bp = cap_tf.paragraphs[0] if b_idx == 0 else cap_tf.add_paragraph()
                bp.text = b
                bp.font.size = Pt(10)
                bp.font.color.rgb = COLOR_TEXT_MUTED
                bp.font.name = "Segoe UI"
                bp.space_after = Pt(4)

        return card

    # =========================================================================
    # SLIDE 1: TITLE & HERO UI SHOWCASE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    # Left Column: Title, Subtitle, Overview, Feature Cards
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(1.2), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_ORANGE
    bar.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.8), Inches(1.0), Inches(6.0), Inches(2.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p1 = tf.paragraphs[0]
    p1.text = "AI ROUNDTABLE"
    p1.font.size = Pt(42)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"

    p2 = tf.add_paragraph()
    p2.text = "Autonomous Multi-Agent Podcast Studio & Router"
    p2.font.size = Pt(19)
    p2.font.bold = True
    p2.font.color.rgb = COLOR_ORANGE
    p2.font.name = "Segoe UI"

    p3 = tf.add_paragraph()
    p3.text = "An open-source interactive broadcast platform where distinct AI personas debate unscripted philosophical and technical battlegrounds with sub-20ms audience barge-in, persistent episodic memory, and ElevenLabs voice aesthetics."
    p3.font.size = Pt(11.5)
    p3.font.color.rgb = COLOR_TEXT_MUTED
    p3.font.name = "Segoe UI"
    p3.space_before = Pt(8)

    # 3 Feature Summary Cards on Left
    s1_cards = [
        ("Autonomous A2A Protocol", "IEEE A2A bus coordinating 3 personas through unscripted dynamic conflict.", COLOR_PURPLE),
        ("Sub-20ms Voice Interruption", "Dual-engine STT (Web Speech + 16kHz PCM WAV) for instant audience barge-in.", COLOR_ORANGE),
        ("Episodic Memory & Fine-Tuning", "50+ turn context ledger with claim contradiction tracking and ChatML export.", COLOR_BLUE)
    ]
    for i, (head, desc, acc) in enumerate(s1_cards):
        cy = Inches(3.6 + i * 1.15)
        add_card(s1, Inches(0.8), cy, Inches(6.0), Inches(1.0))
        
        # Indicator strip
        istrip = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), cy, Inches(0.08), Inches(1.0))
        istrip.fill.solid()
        istrip.fill.fore_color.rgb = acc
        istrip.line.fill.background()

        ctb = s1.shapes.add_textbox(Inches(1.05), cy + Inches(0.1), Inches(5.6), Inches(0.8))
        ctf = ctb.text_frame
        ctf.word_wrap = True
        cp1 = ctf.paragraphs[0]
        cp1.text = head
        cp1.font.size = Pt(13)
        cp1.font.bold = True
        cp1.font.color.rgb = COLOR_WHITE
        cp1.font.name = "Segoe UI"

        cp2 = ctf.add_paragraph()
        cp2.text = desc
        cp2.font.size = Pt(10.5)
        cp2.font.color.rgb = COLOR_TEXT_MUTED
        cp2.font.name = "Segoe UI"

    # Right Column: Hero Studio Screenshot Frame
    add_image_card(
        s1, 
        left=Inches(7.2), 
        top=Inches(0.8), 
        width=Inches(5.33), 
        height=Inches(6.0),
        img_path=SS_MAIN,
        title_text="LIVE STUDIO INTERFACE (ELEVENLABS AESTHETIC)",
        accent_color=COLOR_ORANGE,
        bullets=[
            "• Harmonic Particle Sphere: 220px canvas orb with sine-modulated membrane responding to speech frequencies",
            "• Real-Time Audio Telemetry: 32-band RMS spectrum analyzer with live vocal energy gate threshold",
            "• Live Multi-Agent Dialogue: Instant turn transcription, speaker badges, and 1-click '+ New Conversation' flow"
        ]
    )

    # =========================================================================
    # SLIDE 2: SYSTEM ARCHITECTURE & 3-TIER WORKFLOW
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)

    tb = s2.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "SYSTEM ARCHITECTURE & WORKFLOW"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"
    p2 = tf.add_paragraph()
    p2.text = "Three-tier distributed architecture linking interactive browser telemetry to local/cloud reasoning and voice synthesis"
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_ORANGE
    p2.font.name = "Segoe UI"

    tiers = [
        ("TIER 1: CLIENT STUDIO", "Frontend Experience & Telemetry", [
            ("ElevenLabs Particle Sphere", "Interactive 220px harmonic canvas visualizer with sine-modulated membrane physics"),
            ("Dual-Engine Voice Capture", "Live Web Speech API preview + in-browser 16kHz mono PCM WAV direct encoder"),
            ("Real-Time Telemetry Bar", "32-band spectrum analyzer tracking live vocal energy and speech thresholds"),
            ("Responsive Interruption UI", "Hands-free VAD gate or 1-click push-to-talk with instant audio muting (<20ms)")
        ], COLOR_ORANGE),
        ("TIER 2: A2A ORCHESTRATOR", "Agent Coordination & Agenda Engine", [
            ("IEEE A2A Protocol Bus", "Coordinates turn deliberation: Proposals, Challenges, Syntheses, and Yields"),
            ("Topic & Battlegrounds", "Curated thematic blueprints mapping core trade-offs (AI, Transit, Fusion, UBI)"),
            ("Novelty Rules Engine", "Deduplicates phrases and injects novelty directives to prevent circular loops"),
            ("WebSocket Event Hub", "Bi-directional event sync streaming turn states, A2A traces, and audio blobs")
        ], COLOR_BLUE),
        ("TIER 3: BACKEND WORKERS", "Reasoning, Voice & Episodic Memory", [
            ("Debate Memory Engine", "Tracks full conversation history, panelist stance ledgers, and audience questions"),
            ("Multi-Provider LLM Worker", "Local Ollama (Llama 3.2), OpenAI-compatible (Groq 70B), or procedural fallback"),
            ("ElevenLabs Voice Layer", "Flash v2.5 low-latency neural TTS with pitch-modulated harmonic fallback audio"),
            ("Fine-Tuning Dataset Exporter", "Generates ShareGPT and OpenAI ChatML JSONL datasets for model training")
        ], COLOR_EMERALD)
    ]

    for i, (title, subtitle, bullets, acc) in enumerate(tiers):
        tx = Inches(0.8 + i * 3.95)
        ty = Inches(1.75)
        tw = Inches(3.8)
        th = Inches(4.35)
        add_card(s2, tx, ty, tw, th)

        sbar = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, tx, ty, tw, Inches(0.08))
        sbar.fill.solid()
        sbar.fill.fore_color.rgb = acc
        sbar.line.fill.background()

        ttb = s2.shapes.add_textbox(tx + Inches(0.22), ty + Inches(0.18), tw - Inches(0.44), th - Inches(0.3))
        ttf = ttb.text_frame
        ttf.word_wrap = True

        p_t = ttf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = acc
        p_t.font.name = "Segoe UI"

        p_sub = ttf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(10.5)
        p_sub.font.color.rgb = COLOR_WHITE
        p_sub.font.name = "Segoe UI"

        for b_title, b_desc in bullets:
            pb1 = ttf.add_paragraph()
            pb1.text = f"• {b_title}"
            pb1.font.size = Pt(11)
            pb1.font.bold = True
            pb1.font.color.rgb = COLOR_WHITE
            pb1.font.name = "Segoe UI"
            pb1.space_before = Pt(4)

            pb2 = ttf.add_paragraph()
            pb2.text = f"   {b_desc}"
            pb2.font.size = Pt(10)
            pb2.font.color.rgb = COLOR_TEXT_MUTED
            pb2.font.name = "Segoe UI"

    # Bottom Full-Width Pipeline Flow Bar
    flow_bar = add_card(s2, Inches(0.8), Inches(6.25), Inches(11.7), Inches(0.85))
    flow_tb = s2.shapes.add_textbox(Inches(0.9), Inches(6.3), Inches(11.5), Inches(0.75))
    flow_tf = flow_tb.text_frame
    flow_tf.word_wrap = True
    fp1 = flow_tf.paragraphs[0]
    fp1.text = "END-TO-END EXECUTION PIPELINE"
    fp1.font.size = Pt(10)
    fp1.font.bold = True
    fp1.font.color.rgb = COLOR_ORANGE
    fp1.font.name = "Segoe UI"

    fp2 = flow_tf.add_paragraph()
    fp2.text = "Microphone (16kHz PCM WAV)  ➔  Sub-20ms Interruption Gate  ➔  Fast STT (Google SR / Whisper)  ➔  Episodic Memory Query  ➔  LLM Reasoning (Llama / Groq)  ➔  ElevenLabs Neural Audio  ➔  Visualizer Orb Flare"
    fp2.font.size = Pt(10.5)
    fp2.font.bold = True
    fp2.font.color.rgb = COLOR_WHITE
    fp2.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 3: THE 3 AUTONOMOUS PERSONAS & A2A DYNAMICS
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)

    tb = s3.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "THE 3 AUTONOMOUS AI PERSONAS"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"
    p2 = tf.add_paragraph()
    p2.text = "Engineered podcast personalities with distinct philosophical conviction, voice profiles, and direct conflict dynamics"
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_ORANGE
    p2.font.name = "Segoe UI"

    personas = [
        ("SARAH", "Host & Executive Moderator", "Rachel / Sarah (EXAVITQu4vr4xnSDxMaL)", COLOR_PURPLE,
         "Direct, incisive, fast-paced, unsparing",
         "Drives the broadcast, cuts through evasion, confronts guests with trade-offs, and weaves listener interruptions into the core debate.",
         [
             "Zero hollow pleasantries ('Welcome', 'Thanks for having me')",
             "Pinpoints the blind spot in the opponent's argument immediately",
             "Demands concrete mechanisms instead of corporate platitudes",
             "Broadcast-ready cadence: 2 crisp, high-impact spoken sentences"
         ]),
        ("CHARLIE", "AI Accelerationist & Systems Hacker", "Charlie (IKne3meq5aSn9XLyUdCD)", COLOR_BLUE,
         "Pragmatic, razor-sharp, realistic, blunt",
         "Frontier systems engineer advocating for open weights, local compute ownership, cryptographic verification, and software freedom.",
         [
             "Argues closed monopolies create fragile single points of failure",
             "Asserts open inspection is the only scalable defense against threats",
             "Rebuts regulatory bans with technical feasibility realities",
             "Never uses canned cheerleader slang; jumps straight to mechanisms"
         ]),
        ("ROGER", "AI Governance Scholar & Policy Fellow", "Roger (CwhRBWXzGAHq8TQ4Fs17)", COLOR_EMERALD,
         "Analytical, urgent, grounded, unsparing",
         "Technology policy researcher exposing systemic risks, market externalities, and irreversible hazards in unaligned technology.",
         [
             "Cuts through Silicon Valley techno-solutionism and hype",
             "Highlights physical victims, democratic erosion, and failure modes",
             "Directly dismantles the false analogy between software and dual-use models",
             "Grounds discussions in enforceable public accountability frameworks"
         ])
    ]

    for i, (name, role, voice, acc, tone, bio, traits) in enumerate(personas):
        px = Inches(0.8 + i * 3.95)
        py = Inches(1.75)
        pw = Inches(3.8)
        ph = Inches(5.35)
        add_card(s3, px, py, pw, ph)

        sbar = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px, py, pw, Inches(0.08))
        sbar.fill.solid()
        sbar.fill.fore_color.rgb = acc
        sbar.line.fill.background()

        ptb = s3.shapes.add_textbox(px + Inches(0.25), py + Inches(0.2), pw - Inches(0.5), ph - Inches(0.4))
        ptf = ptb.text_frame
        ptf.word_wrap = True

        p_name = ptf.paragraphs[0]
        p_name.text = name
        p_name.font.size = Pt(20)
        p_name.font.bold = True
        p_name.font.color.rgb = acc
        p_name.font.name = "Segoe UI"

        p_role = ptf.add_paragraph()
        p_role.text = role
        p_role.font.size = Pt(11)
        p_role.font.bold = True
        p_role.font.color.rgb = COLOR_WHITE
        p_role.font.name = "Segoe UI"

        p_voice = ptf.add_paragraph()
        p_voice.text = f"Voice: {voice}"
        p_voice.font.size = Pt(9.5)
        p_voice.font.color.rgb = COLOR_TEXT_MUTED
        p_voice.font.name = "Segoe UI"

        p_bio = ptf.add_paragraph()
        p_bio.text = f"\n{bio}"
        p_bio.font.size = Pt(11)
        p_bio.font.color.rgb = COLOR_TEXT_MUTED
        p_bio.font.name = "Segoe UI"

        p_rule_title = ptf.add_paragraph()
        p_rule_title.text = "\nCore Conversational Directives:"
        p_rule_title.font.size = Pt(11)
        p_rule_title.font.bold = True
        p_rule_title.font.color.rgb = COLOR_WHITE
        p_rule_title.font.name = "Segoe UI"

        for trait in traits:
            pt = ptf.add_paragraph()
            pt.text = f"• {trait}"
            pt.font.size = Pt(10)
            pt.font.color.rgb = COLOR_TEXT_MUTED
            pt.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 4: REAL-TIME BARGE-IN & STT WORKFLOW + SCREENSHOT
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)

    tb = s4.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "REAL-TIME BARGE-IN INTERRUPTION & STT WORKFLOW"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"
    p2 = tf.add_paragraph()
    p2.text = "Zero-fail speech transcription and sub-20ms instant muting for live conversational barge-in"
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_ORANGE
    p2.font.name = "Segoe UI"

    # Left Side: 4 Pipeline Cards (2x2 Grid)
    steps = [
        ("1. VOICE DETECTION", "Auto-VAD or Push-To-Talk", [
            "In-browser AudioContext captures uncompressed 16kHz mono WAV",
            "Web Speech API streams instant interim transcript preview",
            "Zero ffmpeg dependency; pure native browser audio tapping"
        ], COLOR_ORANGE),
        ("2. INSTANT BARGE-IN CUTOFF", "Sub-20ms Audio Preemption", [
            "Immediately pauses playing HTML5 audio element",
            "Halts turn timers and shifts visualizer orb to Listening state",
            "Broadcasts interruption event to all connected WebSocket clients"
        ], COLOR_PURPLE),
        ("3. MULTI-TIER STT RESOLUTION", "Zero-Fail Speech Pipeline", [
            "Tier 1: Browser Web Speech text (0ms local latency)",
            "Tier 2: Python built-in Google Speech Recognition (~300ms)",
            "Tier 3: Groq Cloud Whisper API (<250ms ultra-fast)",
            "Tier 4: Local whisper.cpp for offline environments"
        ], COLOR_BLUE),
        ("4. NATURAL AGENT REACTION", "In-Character Floor Yield", [
            "Smart regex parses target panelist from speech utterance",
            "Active speaker yields floor ('Hold on—', 'Wait, look...')",
            "Addresses audience challenge before resuming debate",
            "Logs question to episodic memory ledger as an open claim"
        ], COLOR_EMERALD)
    ]

    for idx, (title, subtitle, bullets, acc) in enumerate(steps):
        col = idx % 2
        row = idx // 2
        cx = Inches(0.8 + col * 3.1)
        cy = Inches(1.75 + row * 2.65)
        cw = Inches(2.95)
        ch = Inches(2.45)
        add_card(s4, cx, cy, cw, ch)

        sbar = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, cw, Inches(0.06))
        sbar.fill.solid()
        sbar.fill.fore_color.rgb = acc
        sbar.line.fill.background()

        stb = s4.shapes.add_textbox(cx + Inches(0.18), cy + Inches(0.12), cw - Inches(0.36), ch - Inches(0.25))
        stf = stb.text_frame
        stf.word_wrap = True

        p_num = stf.paragraphs[0]
        p_num.text = title
        p_num.font.size = Pt(12)
        p_num.font.bold = True
        p_num.font.color.rgb = acc
        p_num.font.name = "Segoe UI"

        p_s = stf.add_paragraph()
        p_s.text = subtitle
        p_s.font.size = Pt(10)
        p_s.font.bold = True
        p_s.font.color.rgb = COLOR_WHITE
        p_s.font.name = "Segoe UI"

        for b in bullets:
            pb = stf.add_paragraph()
            pb.text = f"• {b}"
            pb.font.size = Pt(9.5)
            pb.font.color.rgb = COLOR_TEXT_MUTED
            pb.font.name = "Segoe UI"

    # Right Side: Screenshot Card of Speaking State & Particle Burst
    add_image_card(
        s4,
        left=Inches(7.2),
        top=Inches(1.75),
        width=Inches(5.33),
        height=Inches(5.35),
        img_path=SS_BURST,
        title_text="AUDIO-REACTIVE PARTICLE ORB (LIVE BROADCAST)",
        accent_color=COLOR_ORANGE,
        bullets=[
            "• Dynamic Frequency Membrane: 220px particle sphere dynamically expands and flares with speaker amplitude",
            "• Sub-20ms Audio Preemption: Playback instantly freezes the millisecond audience vocal energy crosses the VAD gate",
            "• Natural Conversational Yield: Panelist acknowledges the listener challenge in-character before returning to the topic"
        ]
    )

    # =========================================================================
    # SLIDE 5: LONG-TERM EPISODIC MEMORY & FINE-TUNING + SCREENSHOT
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)

    tb = s5.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "LONG-TERM EPISODIC MEMORY & FINE-TUNING"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"
    p2 = tf.add_paragraph()
    p2.text = "Persistent conversational awareness, panelist stance ledgers, and automated dataset extraction for model training"
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_ORANGE
    p2.font.name = "Segoe UI"

    # Left Column: Memory Engine Features
    mx = Inches(0.8)
    my = Inches(1.75)
    mw = Inches(3.6)
    mh = Inches(5.35)
    add_card(s5, mx, my, mw, mh)

    mbar = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, mx, my, mw, Inches(0.08))
    mbar.fill.solid()
    mbar.fill.fore_color.rgb = COLOR_BLUE
    mbar.line.fill.background()

    mtb = s5.shapes.add_textbox(mx + Inches(0.2), my + Inches(0.18), mw - Inches(0.4), mh - Inches(0.35))
    mtf = mtb.text_frame
    mtf.word_wrap = True

    mp1 = mtf.paragraphs[0]
    mp1.text = "EPISODIC MEMORY ENGINE"
    mp1.font.size = Pt(15)
    mp1.font.bold = True
    mp1.font.color.rgb = COLOR_BLUE
    mp1.font.name = "Segoe UI"

    m_features = [
        ("Zero Context Truncation", "Replaced hardcoded 4-turn slicing with dynamic episodic context assembly accommodating 50+ turn debates."),
        ("Panelist Stance Ledger", "Tracks propositions asserted by Sarah, Charlie, and Roger. Personas cite and counter earlier claims by name."),
        ("Audience Inquiries Tracker", "Records every audience challenge, tracking whether it has been resolved or remains an open dispute."),
        ("Running Narrative Arc", "Generates concise running syntheses of key debate tensions injected directly into LLM prompts.")
    ]
    for title, desc in m_features:
        p = mtf.add_paragraph()
        p.text = f"✓ {title}"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.font.name = "Segoe UI"
        p.space_before = Pt(6)

        pd = mtf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(9.5)
        pd.font.color.rgb = COLOR_TEXT_MUTED
        pd.font.name = "Segoe UI"

    # Center Column: Memory Drawer Screenshot
    add_image_card(
        s5,
        left=Inches(4.65),
        top=Inches(1.75),
        width=Inches(4.65),
        height=Inches(5.35),
        img_path=SS_MEMORY,
        title_text="DEBATE MEMORY & CLAIMS DRAWER (LIVE MODAL)",
        accent_color=COLOR_BLUE,
        bullets=[
            "• Active Claim Ledger: Live proposition tracking per persona with contradiction detection",
            "• Open Disputes Matrix: Unresolved listener inquiries flagged for future round resolution",
            "• Running Narrative Arc: Real-time debate synthesis maintaining multi-turn continuity"
        ]
    )

    # Right Column: Fine-Tuning Pipeline
    fx = Inches(9.55)
    fy = Inches(1.75)
    fw = Inches(2.98)
    fh = Inches(5.35)
    add_card(s5, fx, fy, fw, fh)

    fbar = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, fx, fy, fw, Inches(0.08))
    fbar.fill.solid()
    fbar.fill.fore_color.rgb = COLOR_EMERALD
    fbar.line.fill.background()

    ftb = s5.shapes.add_textbox(fx + Inches(0.18), fy + Inches(0.18), fw - Inches(0.36), fh - Inches(0.35))
    ftf = ftb.text_frame
    ftf.word_wrap = True

    fp1 = ftf.paragraphs[0]
    fp1.text = "FINE-TUNING EXPORT"
    fp1.font.size = Pt(15)
    fp1.font.bold = True
    fp1.font.color.rgb = COLOR_EMERALD
    fp1.font.name = "Segoe UI"

    f_features = [
        ("Multi-Format Export", "1-Click download of sessions in OpenAI ChatML and ShareGPT JSONL."),
        ("Tooling Integration", "Ready for Unsloth, Axolotl, LLaMA-Factory, and OpenAI APIs."),
        ("Interruption Markers", "Formats turns with authentic floor yields and challenge cues."),
        ("Broadcast Seed Data", "Includes benchmark debates on AI Safety, Compute Ownership, and Energy.")
    ]
    for title, desc in f_features:
        p = ftf.add_paragraph()
        p.text = f"✓ {title}"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.font.name = "Segoe UI"
        p.space_before = Pt(6)

        pd = ftf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(9.5)
        pd.font.color.rgb = COLOR_TEXT_MUTED
        pd.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 6: TECH STACK MATRIX & STUDIO CONTROLS + SCREENSHOT
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)

    tb = s6.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "PRODUCTION TECH STACK & STUDIO CONTROLS"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"
    p2 = tf.add_paragraph()
    p2.text = "Full-stack specifications, fallback guarantees, and zero-cost local developer experience"
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_ORANGE
    p2.font.name = "Segoe UI"

    # Left Side: 4 Production Specs Cards (2x2 Grid)
    specs = [
        ("Voice Layer (TTS)", "ElevenLabs Flash v2.5", "Ultra-low-latency neural audio with persona voice IDs; graceful procedural modulated fallback audio when API key is unconfigured.", COLOR_ORANGE),
        ("Speech-to-Text (STT)", "Dual-Engine Hybrid STT", "Browser Web Speech API streaming + pure Python 16kHz WAV Google SR + Groq Whisper. 0 ffmpeg binary dependency.", COLOR_EMERALD),
        ("Reasoning Engine (LLM)", "Multi-Provider LLM", "Supports local Ollama (Llama 3.2 3B), Groq Llama 3.3 70B, OpenAI-compatible endpoints, and procedural generator.", COLOR_BLUE),
        ("New Conversation Flow", "1-Click Full State Reset", "Dedicated endpoint and UI button resetting memory, claims ledgers, and transcript for instant fresh debate topics.", COLOR_AMBER)
    ]

    for idx, (head, tech, details, acc) in enumerate(specs):
        col = idx % 2
        row = idx // 2
        cx = Inches(0.8 + col * 3.1)
        cy = Inches(1.75 + row * 2.65)
        cw = Inches(2.95)
        ch = Inches(2.45)
        add_card(s6, cx, cy, cw, ch)

        sbar = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, cw, Inches(0.06))
        sbar.fill.solid()
        sbar.fill.fore_color.rgb = acc
        sbar.line.fill.background()

        stb = s6.shapes.add_textbox(cx + Inches(0.18), cy + Inches(0.12), cw - Inches(0.36), ch - Inches(0.25))
        stf = stb.text_frame
        stf.word_wrap = True

        p_h = stf.paragraphs[0]
        p_h.text = head
        p_h.font.size = Pt(11)
        p_h.font.bold = True
        p_h.font.color.rgb = acc
        p_h.font.name = "Segoe UI"

        p_t = stf.add_paragraph()
        p_t.text = tech
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_WHITE
        p_t.font.name = "Segoe UI"

        p_d = stf.add_paragraph()
        p_d.text = details
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = COLOR_TEXT_MUTED
        p_d.font.name = "Segoe UI"
        p_d.space_before = Pt(4)

    # Right Side: Settings & Tuning Controls Screenshot Card
    add_image_card(
        s6,
        left=Inches(7.2),
        top=Inches(1.75),
        width=Inches(5.33),
        height=Inches(5.35),
        img_path=SS_SETTINGS,
        title_text="STUDIO SETTINGS & TUNING CONTROLS (LIVE MODAL)",
        accent_color=COLOR_AMBER,
        bullets=[
            "• Interruption Sensitivity: Real-time slider adjusting RMS vocal energy threshold for barge-in",
            "• Turn-Taking Cadence: Configurable pacing controls (0.5s rapid-fire to 3.0s broadcast tempo)",
            "• Chroma Key & Memory Depth: Green-screen mode for live streaming and adjustable context recall limits"
        ]
    )

    out_path = "ppt_airoundtable.pptx"
    prs.save(out_path)
    print(f"Presentation successfully created at: {out_path} (Size: {os.path.getsize(out_path):,} bytes)")
    return out_path

if __name__ == "__main__":
    create_deck()
