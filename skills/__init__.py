from classifier.registry import SkillRegistry

# from skills.alarm.skill import SKILL as alarm
# from skills.weather.skill import SKILL as weather
# from skills.music.skill import SKILL as music
from skills.voice_repeat.skill import SKILL as voice_repeat


def load_skills():

    registry = SkillRegistry()

    for skill in [
        voice_repeat
    ]:
        registry.register(skill)

    return registry