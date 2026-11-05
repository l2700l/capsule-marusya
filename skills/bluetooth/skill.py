
import re

from classifier.base import SkillDefinition, BaseSkill
from protocol import Response
from skills.base import SkillRequest


class BluetoothSkill(BaseSkill):

    definition = SkillDefinition(
        name="bluetooth",

        rules=[
            r"\b(bluetooth|блютуз|блютус)\b",
            r"\b(включи|выключи|отключи|активируй)\b.*\b(bluetooth|блютуз|блютус)\b",
        ],

        examples=[
            "Включи блютуз",
            "Выключи блютуз",
            "Отключи Bluetooth",
            "Активируй Bluetooth",
            "Включи Bluetooth",
        ],

        priority=10,
    )

    async def handle(self, request: SkillRequest):

        text = request.text.strip()
        normalized = text.lower()

        if re.search(r"\b(выключи|отключи|деактивируй)\b", normalized):
            enabled = False
            intent = "bluetooth.off"

        elif re.search(r"\b(включи|активируй|запусти)\b", normalized):
            enabled = True
            intent = "bluetooth.on"

        else:
            return (
                Response(
                    skill="bluetooth",
                    intent="bluetooth.unknown",
                    asr_text=text,
                )
                .say("Включить или выключить Bluetooth?")
            )

        return (
            Response(
                skill="bluetooth",
                intent=intent,
                asr_text=text,
            )
            .bluetooth(enabled)
        )


SKILL = BluetoothSkill.definition
SKILL.handler = BluetoothSkill().handle
