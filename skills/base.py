from dataclasses import dataclass
from typing import Any
from core.context import ContextManager

@dataclass
class SkillRequest:
    text: str
    session_id: str
    classification: dict
    context: ContextManager
    stt_result: Any = None