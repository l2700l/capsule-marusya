from dataclasses import dataclass, field
from typing import Callable


@dataclass
class SkillDefinition:
    name: str
    rules: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    priority: int = 0
    handler: Callable | None = None


class BaseSkill:

    definition: SkillDefinition

    async def handle(self, request):
        raise NotImplementedError