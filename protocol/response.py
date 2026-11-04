"""Builder for server responses that instruct the Capsule to perform actions."""
from __future__ import annotations

import json
import uuid
from typing import Any, Mapping

from . import commands as cmd
from .display import show_text


class Response:
    """Fluent builder for the ``qid`` / ``result`` protocol envelope.

    ``to_dict()`` returns a complete response. When returned from the existing
    route registry, ``invoke_route`` may replace the qid with its own request id.
    """
    def __init__(self, *, skill: str = "unknown", intent: str = "unknown",
                 asr_text: str = "", secure: bool = False, qid: str | None = None,
                 controls: list[dict[str, Any]] | None = None,
                 extra_result: Mapping[str, Any] | None = None):
        self.qid = qid or uuid.uuid4().hex
        self.skill = skill
        self.intent = intent
        self.asr_text = asr_text
        self.secure = secure
        self.commands: list[dict[str, Any]] = []
        self.controls: list[dict[str, Any]] = list(controls or [])
        self.extra_result = dict(extra_result or {})

    def add(self, command: Mapping[str, Any]) -> "Response":
        if "type" not in command:
            raise ValueError("command must contain a 'type' field")
        self.commands.append(dict(command))
        return self

    def add_control(self, control: Mapping[str, Any]) -> "Response":
        if "type" not in control:
            raise ValueError("control must contain a 'type' field")
        self.controls.append(dict(control))
        return self

    def say(self, text: str, **options: Any) -> "Response":
        return self.add(cmd.tts(text, **options))

    def delay(self, milliseconds: int) -> "Response":
        return self.add(cmd.delay(milliseconds))

    def listen(self, **options: Any) -> "Response":
        return self.add(cmd.listen(**options))

    def pretty_mode(self, enabled: bool = True) -> "Response":
        return self.add(cmd.pretty_mode(enabled))

    def bluetooth(self, enabled: bool = True) -> "Response":
        return self.add(cmd.bluetooth(enabled))

    def light_demo(self, enabled: bool = True) -> "Response":
        return self.add(cmd.light_demo(enabled))

    def start_timer(self, seconds: int) -> "Response":
        return self.add(cmd.timer(seconds))

    def cancel_timer(self) -> "Response":
        return self.add(cmd.cancel_timer())

    def show_digits(self, text: str, **options: Any) -> "Response":
        return self.add(show_text(text, **options))

    def play_url(self, url: str, **options: Any) -> "Response":
        return self.add(cmd.media(url, **options))

    def play_radio(self, url: str, *, title: str, artist: str,
                   cover_url: str = "", **options: Any) -> "Response":
        options.setdefault("media_type", 2)
        options.setdefault("source_type", "radio")
        options.setdefault("skill_name", "radio")
        return self.add(cmd.media(url, title=title, artist=artist,
                                  cover_url=cover_url, **options))

    def next_track(self) -> "Response":
        return self.control("next")

    def previous_track(self) -> "Response":
        return self.control("previous")

    def pause(self) -> "Response":
        return self.control("pause")

    def resume(self) -> "Response":
        return self.control("resume")

    def shuffle(self) -> "Response":
        return self.control("shuffle")

    def set_volume(self, level: int) -> "Response":
        if not 0 <= level <= 100:
            raise ValueError("volume level must be between 0 and 100")
        return self.control("volume", level=level)

    def control(self, action: str, **fields: Any) -> "Response":
        return self.add_control(cmd.control(action, **fields))

    def settings(self, settings: Mapping[str, Any], *, action_text: str | None = None) -> "Response":
        command: dict[str, Any] = {"type": "general_settings_v1", "settings": dict(settings)}
        if action_text is not None:
            command["action_text"] = action_text
        return self.add(command)

    def night_mode(self, settings: Mapping[str, Any]) -> "Response":
        return self.add({"type": "night_mode_settings_v1", "settings": dict(settings)})

    def alarm_settings(self, alarms: list[Mapping[str, Any]]) -> "Response":
        return self.add({"type": "alarms_settings_v1", "alarms": [dict(alarm) for alarm in alarms]})

    def hint(self, *, subscription_required: bool = False) -> "Response":
        return self.add({"type": "hint", "subscription_required_hint": subscription_required})

    def raw_command(self, command_type: str, **fields: Any) -> "Response":
        return self.add(cmd.raw_command(command_type, **fields))

    def to_result_dict(self) -> dict[str, Any]:
        result = {
            **self.extra_result,
            "commands": [dict(command) for command in self.commands],
            "controls": [dict(control) for control in self.controls],
            "skill": self.skill,
            "asr_text": self.asr_text,
            "secure": self.secure,
            "intent": self.intent,
        }
        return result

    def to_dict(self) -> dict[str, Any]:
        return {"qid": self.qid, "result": self.to_result_dict()}

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))
