from classifier.base import SkillDefinition


class SkillRegistry:

    def __init__(self):
        self.skills: dict[str, SkillDefinition] = {}

    def register(self, definition: SkillDefinition):
        if definition.name in self.skills:
            raise ValueError(
                f"Skill already registered: {definition.name}"
            )

        self.skills[definition.name] = definition

    def get(self, name: str):
        return self.skills.get(name)

    def all(self):
        return list(self.skills.values())

    def get_rules(self):
        return {
            skill.name: skill.rules
            for skill in self.skills.values()
        }

    def get_examples(self):
        return {
            skill.name: skill.examples
            for skill in self.skills.values()
        }