"""Agent-to-Agent (A2A) Protocol implementation for AI Roundtable Podcast.
Complies with the hackathon specification for structured multi-agent communication.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
import time
import uuid
from pydantic import BaseModel, Field

class A2AIntent(str, Enum):
    OPEN_ROUNDTABLE = "OPEN_ROUNDTABLE"
    PROPOSAL = "PROPOSAL"              # Stating core thesis or builder vision
    CHALLENGE = "CHALLENGE"            # Vehement disagreement / counter-argument
    ELABORATE = "ELABORATE"            # Building on a point with technical evidence
    CROSS_EXAMINE = "CROSS_EXAMINE"    # Demanding proof or posing a tough dilemma
    SYNTHESIZE = "SYNTHESIZE"          # Host resolving tension and pushing new angle
    MODERATE = "MODERATE"              # Host steering or resolving a deadlock
    AUDIENCE_CHALLENGE = "AUDIENCE_CHALLENGE"  # Interruption routing
    YIELD_FLOOR = "YIELD_FLOOR"        # Passing turn to specific panelist

class A2AMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"a2a_{uuid.uuid4().hex[:8]}")
    timestamp: float = Field(default_factory=time.time)
    sender_id: str                      # host | technologist | ethicist | audience
    receiver_id: str                    # host | technologist | ethicist | all
    intent: A2AIntent
    dimension: str                      # Substantive angle (e.g., "Weaponization", "Economic Moats")
    claim_summary: str                  # 1-sentence synopsis of the argument
    priority: float = 0.5               # Urgency of speaking (0.0 to 1.0)
    context_ref: Optional[str] = None   # Reference to previous message/claim

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "intent": self.intent.value if isinstance(self.intent, A2AIntent) else str(self.intent),
            "dimension": self.dimension,
            "claim_summary": self.claim_summary,
            "priority": self.priority,
            "context_ref": self.context_ref
        }

class A2ARoundtableCoordinator:
    """Coordinates the A2A communication bus and determines debate floor allocation."""
    def __init__(self):
        self.message_log: List[A2AMessage] = []
        self.established_claims: List[str] = []
        self.turn_counter: int = 0

    def record_message(self, msg: A2AMessage) -> None:
        self.message_log.append(msg)
        if msg.claim_summary and msg.claim_summary not in self.established_claims:
            self.established_claims.append(msg.claim_summary)

    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.message_log[-limit:]]

    def clear(self) -> None:
        self.message_log.clear()
        self.established_claims.clear()
        self.turn_counter = 0
