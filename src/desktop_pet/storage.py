"""Small, atomic JSON store used for memories, todos, stats and whitelists."""

from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any


class JsonStore:
    """Thread-safe JSON file with atomic writes and forgiving reads.

    A corrupt or missing file falls back to a deep copy of ``default`` instead
    of crashing the desktop pet.
    """

    def __init__(self, path: Path, default: Any) -> None:
        self.path = Path(path)
        self.default = default
        self._lock = threading.RLock()

    def load(self) -> Any:
        with self._lock:
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except (OSError, json.JSONDecodeError, ValueError):
                return copy.deepcopy(self.default)

    def save(self, data: Any) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp, self.path)

    def update(self, callback) -> Any:
        """Load, mutate and save in one locked operation."""
        with self._lock:
            data = self.load()
            result = callback(data)
            self.save(data)
            return result
