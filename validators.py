"""Defensive, reusable console input helpers."""
from datetime import date
import re


class CancelInput(Exception):
    """Raised when the user cancels a prompt."""


def _read(prompt):
    try:
        value = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise CancelInput
    if value.casefold() in {"c", "cancel"}:
        raise CancelInput
    return value


def get_int(prompt, min_value=None, max_value=None):
    while True:
        raw = _read(prompt)
        try:
            value = int(raw)
            if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
                raise ValueError
            return value
        except ValueError:
            print("Enter a whole number within the allowed range (or c to cancel).")


def get_float(prompt, min_value=None, max_value=None):
    while True:
        raw = _read(prompt)
        try:
            value = float(raw)
            if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
                raise ValueError
            return value
        except ValueError:
            print("Enter a valid number within the allowed range (or c to cancel).")


def get_nonempty_string(prompt, max_len=120):
    while True:
        value = _read(prompt)
        if value and len(value) <= max_len:
            return value
        print(f"Enter 1 to {max_len} characters (or c to cancel).")


def get_regex_string(prompt, pattern, error_msg="Invalid format"):
    while True:
        value = _read(prompt)
        if re.fullmatch(pattern, value):
            return value
        print(error_msg)


def get_date(prompt, allow_future=True):
    while True:
        value = _read(prompt)
        try:
            parsed = date.fromisoformat(value)
            if not allow_future and parsed > date.today():
                raise ValueError
            return parsed
        except ValueError:
            print("Use YYYY-MM-DD and enter a valid date.")


def get_choice(prompt, options):
    choices = {str(item).casefold(): item for item in options}
    while True:
        value = _read(f"{prompt} ({'/'.join(map(str, options))}): ")
        if value.casefold() in choices:
            return choices[value.casefold()]
        print("Choose one of the listed options.")


def get_yes_no(prompt):
    return get_choice(prompt, ["y", "n"]) == "y"
