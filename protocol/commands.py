"""Typed-ish builders for commands understood by Capsule Neo firmware.

The wire format is intentionally represented as ordinary dictionaries so unknown
fields and newly discovered command types can be supported without changing the API.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Mapping
from tts import generate_audio, save_stream
from tts.qwen import start_stream

def raw_command(command_type: str, **fields: Any) -> dict[str, Any]:
    """Build a command while preserving the firmware's ``type`` field."""
    return {**fields, "type": command_type}



def tts(
    text: str,
    *,
    blocking: bool = True,
    normalize: bool = True,
    force_say: bool = False,
    kws_skip: Any = None,
    encoder: str = "opus",
    encoder_bitrate: int | None = 32,
    encoder_frame_size: int | None = None,
    model_name: str | None = None,
    long_reader_request: bool = False,
    speed: float = 1.0,
    stream_id: str | None = None,
    engine: str = "silero",
) -> dict[str, Any]:
    stream_id = stream_id or str(uuid.uuid4())

    if engine == "qwen":
        if speed != 1.0:
            raise ValueError(
                "Qwen streaming currently supports only speed=1.0"
            )

        start_stream(
            text,
            stream_id,
        )

    elif engine == "silero":
        audio = generate_audio(
            text,
            bitrate=encoder_bitrate or 32,
            speed=speed,
            normalize=normalize,
        )

        save_stream(stream_id, audio)

    else:
        raise ValueError(f"Unknown TTS engine: {engine}")

    return raw_command(
        "tts",
        text=text,
        blocking=blocking,
        normalize=normalize,
        force_say=force_say,
        kws_skip=kws_skip,
        encoder=encoder,
        encoder_bitrate=encoder_bitrate,
        encoder_frame_size=encoder_frame_size,
        model_name=model_name,
        long_reader_request=long_reader_request,
        speed=speed,
        stream_id=stream_id,
    )


def delay(milliseconds: int) -> dict[str, Any]:
    if milliseconds < 0:
        raise ValueError("delay must be >= 0 milliseconds")
    return raw_command("delay", length=milliseconds)


def listen(*, min_waiting_time: float = 4.0, mute_activation_sound: bool = False,
           forced_listen: bool = True, listen_previous_intent: str | None = None,
           callback_data: str | None = None, blocking: bool = True) -> dict[str, Any]:
    if callback_data is None:
        callback: dict[str, Any] = {"forced_listen": forced_listen}
        if listen_previous_intent is not None:
            callback["listen_previous_intent"] = listen_previous_intent
        callback_data = json.dumps(callback, ensure_ascii=False, separators=(",", ":"))
    return raw_command(
        "listen", min_waiting_time=min_waiting_time,
        mute_activation_sound=mute_activation_sound,
        callback_data=callback_data, blocking=blocking,
    )


def pretty_mode(enabled: bool) -> dict[str, Any]:
    return raw_command("pretty_mode", turn_on=bool(enabled))


def bluetooth(enabled: bool) -> dict[str, Any]:
    return raw_command("bluetooth_pair", turn_on=bool(enabled))


def light_demo(enabled: bool) -> dict[str, Any]:
    return raw_command("enter_light_demo" if enabled else "exit_light_demo")


def timer(seconds: int, *, now: float | None = None) -> dict[str, Any]:
    if seconds < 0:
        raise ValueError("timer duration must be >= 0 seconds")
    timestamp = int(time.time() if now is None else now) + seconds
    return raw_command("timer", timestamp=timestamp, cancel=False, timestamp_delta=seconds)


def cancel_timer() -> dict[str, Any]:
    return raw_command("timer", timestamp=0, cancel=True, timestamp_delta=0)


def media(url: str, *, title: str = "", artist: str = "", media_type: int = 1,
          source_type: str = "url", skill_name: str = "music", cover_url: str = "",
          autoplay: bool = True, append: bool = False, action_text: str = "",
          kws_skip: Any = None, need_vk_session: Any = None,
          page_token: Any = None, content_value: Mapping[str, Any] | None = None,
          phrase_id: str | None = None, stat_flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a media command. Metadata can be adjusted as captures teach us more."""
    phrase_id = phrase_id or time.strftime("%Y%m%d-%H%M-%S") + "-" + uuid.uuid4().hex[:12]
    source = {
        "artist": artist,
        "media_type": "radio" if source_type == "radio" else "music",
        "type": source_type,
        "uid": url,
        "phrase_id": phrase_id,
        "skill_name": skill_name,
    }
    meta = {
        "artist": artist, "source": source, "title": title, "url": url,
        "coverUrl": cover_url,
    }
    # Captures show that direct URL playback can start without stat_flags.
    # Keep them opt-in until source-specific values are understood.
    if stat_flags is not None:
        flags = dict(stat_flags)
        encoded_flags = json.dumps(flags, ensure_ascii=False, separators=(",", ":"))
        source["stat_flags"] = encoded_flags
        meta["stat_flags"] = encoded_flags
    return raw_command(
        "media", url=url, meta=meta, media_type=media_type, kws_skip=kws_skip,
        autoplay=autoplay, append=append, event_media_end=None,
        action_text=action_text, content_value=dict(content_value or {}),
        need_vk_session=need_vk_session, page_token=page_token,
    )


_CONTROL_TYPES = {
    "next": "next_control",
    "previous": "previous_control",
    "repeat": "repeat_control",
    "repeat_playlist": "repeat_playlist_control",
    "rewind": "rewind_control",
    "shuffle": "shuffle_control",
    "pause": "pause_control",
    "resume": "resume_control",
    "volume": "volume_control",
}


def control(action: str, **fields: Any) -> dict[str, Any]:
    """Build a playback control; action is a short Python-friendly name."""
    try:
        command_type = _CONTROL_TYPES[action]
    except KeyError as exc:
        raise ValueError(f"unknown control {action!r}; expected one of {', '.join(_CONTROL_TYPES)}") from exc
    defaults: dict[str, Any] = {
        "repeat": {"count": 0},
        "repeat_playlist": {"count": 0},
        "rewind": {"elapsed": 0, "position": 0},
        "volume": {"level": 20},
    }
    return {**defaults.get(action, {}), **fields, "type": command_type}
