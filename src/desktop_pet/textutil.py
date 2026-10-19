"""Small text helpers that do not depend on Kivy (keeps tests lightweight)."""

from __future__ import annotations


def wrap_text(text: str, limit: int = 12) -> list[str]:
    """Wrap text by visual width; CJK characters count as one unit.

    Explicit newlines are preserved, and long English words are hard-wrapped.
    """
    limit = max(4, int(limit))
    lines: list[str] = []
    for raw in (text or "").splitlines() or [""]:
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        while len(line) > limit:
            cut = line.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            lines.append(line[:cut].rstrip())
            line = line[cut:].lstrip()
        lines.append(line)
    return lines or [""]
