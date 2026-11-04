from classifier.registry import SkillRegistry

from skills.alarm.skill import SKILL as alarm
from skills.weather.skill import SKILL as weather
from skills.music.skill import SKILL as music


def load_skills():

    registry = SkillRegistry()

    for skill in [
        alarm,
        weather,
        music,
    ]:
        registry.register(skill)

    return registry