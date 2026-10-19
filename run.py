#!/usr/bin/env python3
"""Run Desktop Pet from a source checkout without installing the package."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from desktop_pet.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
