"""Load externalized YAML prompts (ADR-002).

Why this exists
---------------
Prompts evolve faster than code. Keeping them in ``llm/prompts/*.yaml`` lets
product/HR iterate on wording without touching Python, and makes diffs reviewable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache
def load_prompt(name: str) -> dict[str, Any]:
    """Load ``{name}.yaml`` once per process and return the mapping.

    Expected keys: ``system`` (str) and usually ``user_template`` (str with
    ``.format`` placeholders).
    """
    path = _PROMPTS_DIR / f"{name}.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "system" not in data:
        raise ValueError(f"Prompt file {path} must be a mapping with a 'system' key")
    return data
