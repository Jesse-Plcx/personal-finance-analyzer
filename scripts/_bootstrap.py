from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

ANSI_RESET = "\033[0m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def colorize(text: object, color: str) -> str:
    text = str(text)
    if not USE_COLOR:
        return text
    return f"{color}{text}{ANSI_RESET}"


def amount_text(amount: float, direction: str | None = None) -> str:
    text = f"¥{amount:,.2f}"
    if direction == "收入":
        return colorize(text, ANSI_GREEN)
    if direction == "支出":
        return colorize(text, ANSI_RED)
    if amount > 0:
        return colorize(text, ANSI_GREEN)
    if amount < 0:
        return colorize(text, ANSI_RED)
    return text


def direction_text(direction: str) -> str:
    if direction == "收入":
        return colorize(direction, ANSI_GREEN)
    if direction == "支出":
        return colorize(direction, ANSI_RED)
    return colorize(direction, ANSI_YELLOW)
