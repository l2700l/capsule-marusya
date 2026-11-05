from classifier.registry import SkillRegistry

# from skills.alarm.skill import SKILL as alarm
# from skills.weather.skill import SKILL as weather
# from skills.music.skill import SKILL as music
from skills.voice_repeat.skill import SKILL as voice_repeat
from skills.bluetooth.skill import SKILL as bluetooth
from skills.pretty_mode.skill import SKILL as pretty_mode
from skills.time.skill import SKILL as time
from skills.skill_list.skill import SKILL as skill_list

def load_skills():

    registry = SkillRegistry()
    for skill in [
        voice_repeat,
        bluetooth,
        pretty_mode,
        time,
        skill_list,
    ]:
        registry.register(skill)

    return registry