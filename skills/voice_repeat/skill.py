import re

from classifier.base import SkillDefinition, BaseSkill
from protocol import Response
from skills.base import SkillRequest

class VoiceRepeatSkill(BaseSkill):

    definition = SkillDefinition(
        name="voice_repeat",

        rules=[
            r"\bповторяй за мной\b",
            r"\bповтори за мной\b",
            r"\bскажи за мной\b",
            r"\bповтори\b",
            r"\bхватит повторять\b",
            r"\bперестань повторять\b",
        ],

        examples=[
            "Повторяй за мной",
            "Повтори за мной",
            "Скажи за мной",
            "Повтори привет",
            "Хватит повторять",
        ],

        priority=10,
    )

    async def handle(self, request: SkillRequest):

        text = request.text.strip()
        normalized = text.lower()

        # Выход из режима повторения
        if re.search(
            r"\b(хватит|стоп|перестань|закончить)\b",
            normalized,
        ):
            request.context.clear_active_skill(request.session_id)

            return (
                Response(
                    skill="voice_repeat",
                    intent="voice_repeat.stop",
                    asr_text=text,
                )
                .say("Хорошо, больше не повторяю")
            )

        # Включение режима повторения
        if re.search(
            r"\b(повторяй за мной|повтори за мной|скажи за мной)\b",
            normalized,
        ):
            request.context.set_active_skill(request.session_id, self.definition.name)

            return (
                Response(
                    skill="voice_repeat",
                    intent="voice_repeat.start",
                    asr_text=text,
                )
                .say("Хорошо, я буду повторять за тобой")
                .listen(
                    min_waiting_time=0.0,
                    forced_listen=True,
                    listen_previous_intent="voice_repeat.start",
                )
            )

        # Разовый повтор
        phrase = re.sub(
            r"^\s*повтори\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        if not phrase:
            return (
                Response(
                    skill="voice_repeat",
                    intent="voice_repeat.repeat",
                    asr_text=text,
                )
                .say("Что мне повторить?")
                .listen(
                    min_waiting_time=0.0,
                    forced_listen=True,
                    listen_previous_intent="voice_repeat.repeat",
                )
            )
        print(phrase)
        return (
            Response(
                skill="voice_repeat",
                intent="voice_repeat.repeat",
                asr_text=text,
            )
            .say(phrase)
            .listen(
                min_waiting_time=0.0,
                forced_listen=True,
                listen_previous_intent="voice_repeat.repeat",
            )
        )


SKILL = VoiceRepeatSkill.definition
SKILL.handler = VoiceRepeatSkill().handle