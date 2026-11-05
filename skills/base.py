from dataclasses import dataclass
from typing import Any
from core.context import ContextManager
from classifier.model import ModelProvider
@dataclass
class SkillRequest:
    text: str
    session_id: str
    classification: dict
    context: ContextManager
    semantic_model: ModelProvider
    stt_result: Any = None