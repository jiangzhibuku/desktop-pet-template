"""Character creation toolkit.

This subpackage turns a user-supplied image or a short text description into a
character pack that the desktop-pet runtime can load.  It deliberately depends
only on Pillow + the standard library, so the CLI works without Kivy.
"""

from __future__ import annotations

from .spec import CharacterSpec, parse_prompt

__all__ = ["CharacterSpec", "parse_prompt"]
