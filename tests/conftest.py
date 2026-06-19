"""Pytest path setup and core ADL Lite fixtures.

This conftest is intentionally lightweight — no FDE/FastAPI/SQLAlchemy dependencies.
FDE-specific fixtures live in conftest_fde.py (not auto-loaded by pytest).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
