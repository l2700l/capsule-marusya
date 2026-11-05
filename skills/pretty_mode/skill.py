
import re

from classifier.base import SkillDefinition, BaseSkill
from protocol import Response
from skills.base import SkillRequest


class PrettyModeSkill(BaseSkill):

    definition = SkillDefinition(
        name="pretty_mode",

        rules=[
            r"\b(красивый режим|режим красоты)\b",
            r"\b(включи|выключи|отключи|активируй|скрой)\b.*\b(красивый режим|режим красоты)\b",
            r"\b(включи|выключи|отключи|активируй|скрой)\b.*\b((ми-ми-ми|мимими) режим|режим (ми-ми-ми|мимими))\b",
        ],

        examples=[
            "Включи красивый режим",
            "Выключи красивый режим",
            "Отключи красивый режим",
            "Активируй красивый режим",
            "Включи режим ми-ми-ми",
            "Выключи режим ми-ми-ми",
            "Включи режим мимими",
            "Выключи режим мимими",
            "Покажи глазки",
            "Верни часы",
            "Убери глазки"
        ],

        priority=10,
    )

    async def handle(self, request: SkillRequest):

        text = request.text.strip()
        normalized = text.lower()

        if re.search(r"\b(выключи|отключи|деактивируй|скрой|верни|убери)\b", normalized):
            enabled = False
            intent = "pretty_mode.off"

        elif re.search(r"\b(включи|активируй|запусти|покажи)\b", normalized):
            enabled = True
            intent = "pretty_mode.on"

        else:
            return (
                Response(
                    skill="pretty_mode",
                    intent="pretty_mode.unknown",
                    asr_text=text,
                )
                .say("Включить или выключить красивый режим?")
            )

        return (
            Response(
                skill="pretty_mode",
                intent=intent,
                asr_text=text,
            )
            .pretty_mode(enabled)
        )


SKILL = PrettyModeSkill.definition
SKILL.handler = PrettyModeSkill().handle
