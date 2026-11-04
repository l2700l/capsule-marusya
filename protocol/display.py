"""Seven-segment display helpers for the four-character Capsule clock."""
from __future__ import annotations
from typing import Sequence

# Segment order from the reverse-engineered protocol:
# top, upper-right, lower-right, bottom, lower-left, upper-left, middle.
SEGMENTS = {
    "0": (1, 2, 3, 4, 5, 6), "1": (2, 3), "2": (1, 2, 4, 5, 7),
    "3": (1, 2, 3, 4, 7), "4": (2, 3, 6, 7), "5": (1, 3, 4, 6, 7),
    "6": (1, 3, 4, 5, 6, 7), "7": (1, 2, 3), "8": (1, 2, 3, 4, 5, 6, 7),
    "9": (1, 2, 3, 4, 6, 7),
    "A": (1, 2, 3, 5, 6, 7), "B": (3, 4, 5, 6, 7),
    "C": (1, 4, 5, 6), "D": (2, 3, 4, 5, 7), "E": (1, 4, 5, 6, 7),
    "F": (1, 5, 6, 7), "P": (1, 2, 5, 6, 7),
    "-": (7,), " ": (),
}


def brightness_for_text(text: str, *, on: int = 255, off: int = 0,
                        upper_dot: bool = False, lower_dot: bool = False) -> list[int]:
    """Return 30 brightness values for four characters, two dots and four digits.

    Characters are rendered left-to-right. Unsupported characters raise ValueError
    rather than silently producing a misleading display.
    """
    text = text.upper()
    if len(text) > 4:
        raise ValueError("display text must contain at most 4 characters")
    text = text.ljust(4)
    values = [off] * 30
    for char_index, char in enumerate(text):
        try:
            active_segments = SEGMENTS[char]
        except KeyError as exc:
            raise ValueError(f"unsupported seven-segment character: {char!r}") from exc
        base = 0 if char_index == 0 else 7 if char_index == 1 else 16 if char_index == 2 else 23
        for segment in active_segments:
            values[base + segment - 1] = on
    values[14] = on if upper_dot else off
    values[15] = on if lower_dot else off
    return values


def led_digits_animation(brightness: Sequence[int], *, duration: float = 15.0,
                         seconds: float | None = None, iteration_count: int = 1,
                         blocking: bool = False,
                         action_text: str = "Включаю анимацию дисплея") -> dict:
    if len(brightness) != 30:
        raise ValueError(f"brightness must contain exactly 30 values, got {len(brightness)}")
    if any(not 0 <= int(value) <= 255 for value in brightness):
        raise ValueError("brightness values must be between 0 and 255")
    return {
        "type": "led_digits_animation",
        "frames": [{"brightness": [int(v) for v in brightness], "seconds": seconds, "duration": float(duration)}],
        "iteration_count": int(iteration_count),
        "blocking": bool(blocking),
        "action_text": action_text,
    }


def show_text(text: str, *, duration: float = 15.0, on: int = 255,
              off: int = 0, upper_dot: bool = False, lower_dot: bool = False,
              iteration_count: int = 1, blocking: bool = False,
              action_text: str = "Включаю анимацию дисплея") -> dict:
    return led_digits_animation(
        brightness_for_text(text, on=on, off=off, upper_dot=upper_dot, lower_dot=lower_dot),
        duration=duration, iteration_count=iteration_count, blocking=blocking,
        action_text=action_text,
    )
