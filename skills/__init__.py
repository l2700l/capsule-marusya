from classifier.registry import SkillRegistry

from skills.voice_repeat.skill import SKILL as voice_repeat
from skills.bluetooth.skill import SKILL as bluetooth
from skills.pretty_mode.skill import SKILL as pretty_mode
from skills.time.skill import SKILL as time
from skills.skill_list.skill import SKILL as skill_list
from skills.unknown.skill import SKILL as unknown
from skills.till.skill import SKILL as till
from skills.calculator.skill import SKILL as calculator
from skills.controls.skill import SKILL as controls
from skills.weather.skill import SKILL as weather
from skills.translation.skill import SKILL as translation
from skills.night_mode.skill import SKILL as night_mode
from skills.alarms.skill import SKILL as alarms

def load_skills():

    registry = SkillRegistry()
    for skill in [
        voice_repeat,
        bluetooth,
        pretty_mode,
        time,
        skill_list,
        unknown,
        till,
        calculator,
        controls,
        weather,
        translation,
        night_mode,
        alarms
    ]:
        registry.register(skill)

    return registry