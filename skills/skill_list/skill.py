from classifier.base import SkillDefinition, BaseSkill
from protocol import Response
from skills.base import SkillRequest


class SkillListSkill(BaseSkill):

    definition = SkillDefinition(
        name="skill_list",

        rules=[
            r"\bчто ты умеешь\b",
            r"\bчто ты можешь\b",
            r"\bкакие у тебя есть навыки\b",
            r"\bсписок команд\b",
            r"\bрасскажи о своих возможностях\b",
        ],

        examples=[
            "Что ты умеешь?",
            "Что ты можешь делать?",
            "Какие у тебя есть навыки?",
            "Расскажи о своих возможностях",
            "Какие команды ты понимаешь?",
            "Что можно у тебя спросить?",
        ],

        priority=10,
    )

    async def handle(self, request: SkillRequest):

        return (
            Response(
                skill="skills_list",
                intent="skills_list.show",
                asr_text=request.text,
            )
            .say(
                "Я умею считать, переводить, конвертировать величины, "
                "ставить будильники, напоминать о важно, включать музыку и радио."
            )
        )


SKILL = SkillListSkill.definition
SKILL.handler = SkillListSkill().handle