from __future__ import annotations

from pathlib import Path

from scripts.validate_repository import validate_repository


def test_repository_conformance() -> None:
    root = Path(__file__).resolve().parents[2]
    validate_repository(root)
