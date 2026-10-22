"""Debate Long-Term Memory & Context Engine.

Maintains complete episodic memory across the multi-agent roundtable:
1. Full transcript history with timestamps and speaking turns.
2. Panelist Stance Ledger (tracks established claims per persona).
3. Audience Intervention Tracker (records listener interruptions and resolution status).
4. Running Debate Narrative Arc (condensed synthesis of past discussion).
5. Dynamic Context Assembly for LLM prompt generation (cross-referencing previous arguments by name).
"""
import time
from typing import List, Dict, Any, Optional

class DebateTurn:
    def __init__(
        self,
        turn_index: int,
        speaker_id: str,
        speaker_name: str,
        role: str,
        content: str,
        is_interruption: bool = False,
        target_agent: Optional[str] = None,
        dimension: str = "Core Debate",
        timestamp: Optional[float] = None
    ):
        self.turn_index = turn_index
        self.speaker_id = speaker_id
        self.speaker_name = speaker_name
        self.role = role
        self.content = content.strip()
        self.is_interruption = is_interruption
        self.target_agent = target_agent
        self.dimension = dimension
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "agent_id": self.speaker_id,
            "sender": self.speaker_name,
            "role": self.role,
            "content": self.content,
            "is_interruption": self.is_interruption,
            "target_agent": self.target_agent,
            "dimension": self.dimension,
            "timestamp": self.timestamp
        }


class DebateMemoryEngine:
    def __init__(self, topic: str = "The Future of Open-Source AI"):
        self.topic = topic
        self.turns: List[DebateTurn] = []
        # Persona claim ledger: persona_id -> list of core claims
        self.claims_ledger: Dict[str, List[str]] = {
            "host": [],
            "technologist": [],
            "ethicist": []
        }
        # Audience interventions: list of questions and resolution notes
        self.audience_interventions: List[Dict[str, Any]] = []
        # Running episodic narrative summary
        self.narrative_summary: str = ""
        # Dimension transition history
        self.dimensions_explored: List[str] = []

    def set_topic(self, topic: str, clear_history: bool = True):
        self.topic = topic
        if clear_history:
            self.clear()

    def clear(self):
        self.turns = []
        self.claims_ledger = {
            "host": [],
            "technologist": [],
            "ethicist": []
        }
        self.audience_interventions = []
        self.narrative_summary = ""
        self.dimensions_explored = []

    def record_turn(
        self,
        speaker_id: str,
        speaker_name: str,
        role: str,
        content: str,
        is_interruption: bool = False,
        target_agent: Optional[str] = None,
        dimension: str = "Core Debate"
    ) -> DebateTurn:
        turn_index = len(self.turns) + 1
        turn = DebateTurn(
            turn_index=turn_index,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            role=role,
            content=content,
            is_interruption=is_interruption,
            target_agent=target_agent,
            dimension=dimension
        )
        self.turns.append(turn)

        if dimension and dimension not in self.dimensions_explored:
            self.dimensions_explored.append(dimension)

        # Update persona claims ledger
        if speaker_id in self.claims_ledger and not is_interruption:
            summary = self._extract_core_claim(content)
            if summary and summary not in self.claims_ledger[speaker_id]:
                self.claims_ledger[speaker_id].append(summary)

        # Track audience intervention
        if is_interruption or speaker_id == "audience" or "Audience" in speaker_name:
            self.audience_interventions.append({
                "turn_index": turn_index,
                "question": content,
                "directed_to": target_agent or "all",
                "timestamp": turn.timestamp,
                "answered": False
            })
        elif self.audience_interventions and not self.audience_interventions[-1]["answered"]:
            # Mark the latest audience question as addressed by this turn
            self.audience_interventions[-1]["answered"] = True
            self.audience_interventions[-1]["answered_by"] = speaker_name

        # Incrementally refresh narrative summary if enough turns have passed
        if len(self.turns) % 4 == 0:
            self._update_narrative_summary()

        return turn

    def _extract_core_claim(self, content: str) -> str:
        """Extracts the first 1-2 key proposition sentences from a turn."""
        sentences = [s.strip() for s in content.replace("!", ".").replace("?", ".").split(".") if len(s.strip()) > 15]
        if sentences:
            return sentences[0]
        return content[:120]

    def _update_narrative_summary(self):
        """Creates a concise running episodic summary of the debate arc."""
        recent_claims = []
        if self.claims_ledger["technologist"]:
            recent_claims.append(f"Charlie asserts: {self.claims_ledger['technologist'][-1]}")
        if self.claims_ledger["ethicist"]:
            recent_claims.append(f"Roger argues: {self.claims_ledger['ethicist'][-1]}")
        if self.claims_ledger["host"]:
            recent_claims.append(f"Sarah moderated on: {self.claims_ledger['host'][-1]}")

        unresolved_q = [q["question"] for q in self.audience_interventions[-2:]]
        interventions_summary = f" Recent audience challenge: '{unresolved_q[-1]}'." if unresolved_q else ""

        self.narrative_summary = (
            f"Debate on '{self.topic}'. Key tensions explored across {len(self.dimensions_explored)} dimensions: "
            + "; ".join(recent_claims)
            + interventions_summary
        )

    def get_structured_context(
        self,
        target_persona_id: str,
        current_dimension: str = "Core Debate",
        user_interruption: Optional[str] = None,
        max_verbatim_turns: int = 8
    ) -> Dict[str, Any]:
        """Assembles rich episodic context for the LLM prompt.
        
        Guarantees the persona knows:
        1. All prior claims made by themselves and opponents.
        2. Unresolved or recent audience questions.
        3. The chronological sequence of recent turns.
        """
        # 1. Stance ledger of all panelists
        charlie_claims = self.claims_ledger.get("technologist", [])[-3:]
        roger_claims = self.claims_ledger.get("ethicist", [])[-3:]
        sarah_points = self.claims_ledger.get("host", [])[-2:]

        # 2. Audience questions history
        recent_questions = [
            f"\"{item['question']}\" (addressed to {item.get('directed_to', 'all')})"
            for item in self.audience_interventions[-3:]
        ]

        # 3. Recent verbatim dialogue buffer (last 6-8 turns)
        substantive_turns = [
            t for t in self.turns
            if t.speaker_name not in ["System"] and len(t.content) > 5
        ]
        recent_buffer = substantive_turns[-max_verbatim_turns:]
        formatted_dialogue = []
        for t in recent_buffer:
            tag = f"[Audience Interruption]" if t.is_interruption else f"[{t.speaker_name} - {t.role}]"
            formatted_dialogue.append(f"{tag}: {t.content}")

        # 4. Determine last opposing speaker and their argument
        last_turn = substantive_turns[-1] if substantive_turns else None
        last_speaker_name = last_turn.speaker_name if last_turn else ""
        last_speaker_arg = last_turn.content if last_turn else ""

        return {
            "topic": self.topic,
            "dimension": current_dimension,
            "total_turns": len(self.turns),
            "narrative_summary": self.narrative_summary or f"Active debate discussing '{self.topic}'.",
            "charlie_claims": charlie_claims,
            "roger_claims": roger_claims,
            "sarah_points": sarah_points,
            "recent_audience_questions": recent_questions,
            "recent_dialogue": formatted_dialogue,
            "last_speaker_name": last_speaker_name,
            "last_speaker_arg": last_speaker_arg,
            "active_interruption": user_interruption
        }

    def get_full_history_dicts(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.turns]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "total_turns": len(self.turns),
            "charlie_claims_count": len(self.claims_ledger.get("technologist", [])),
            "roger_claims_count": len(self.claims_ledger.get("ethicist", [])),
            "sarah_points_count": len(self.claims_ledger.get("host", [])),
            "audience_questions_count": len(self.audience_interventions),
            "dimensions_explored": self.dimensions_explored
        }
