#!/usr/bin/env python3
"""Run the character creator from a source checkout.

    python create_pet.py --name 雪球 --prompt "白色小猫，戴红围巾"

After ``pip install -e .`` you can also use ``python -m desktop_pet.creator``
or the ``desktop-pet-create`` console script.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from desktop_pet.creator.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
