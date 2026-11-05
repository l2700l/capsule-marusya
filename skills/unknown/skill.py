from classifier.base import SkillDefinition, BaseSkill
from protocol import Response
from skills.base import SkillRequest


class UnknownSkill(BaseSkill):

    definition = SkillDefinition(
        name="unknown",
        priority=0,
    )

    async def handle(self, request: SkillRequest):

        return (
            Response(
                skill="unknown",
                intent="unknown.default",
                asr_text=request.text,
            )
            .say("Извини, я пока не умею это делать")
        )


SKILL = UnknownSkill.definition
SKILL.handler = UnknownSkill().handle