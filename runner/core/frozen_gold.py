"""Evaluator-only comparison against frozen Gold result identities.

This module deliberately has no database or SQL dependency.  A target may only
submit the identity of a result produced during its own trial.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from jsonschema import Draft202012Validator


class FrozenGoldError(ValueError):
    """Raised when a frozen Gold asset cannot be used safely."""


@dataclass(frozen=True)
class FrozenEvaluation:
    result_equivalent: bool
    reference_result_sha256: str
    duration_ms: float


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        # Tests and controlled deployments may pin an external immutable volume.
        # It is still compared as an exact canonical absolute path and hash.
        return str(path.resolve())


class FrozenGoldEvaluator:
    """Validated immutable Gold identities for one experiment's selected questions."""

    def __init__(self, identities: dict[str, dict[str, Any]]):
        self._identities = identities

    @classmethod
    def preflight(
        cls,
        *,
        root: Path,
        gold_paths: dict[str, str],
        manifest_path: Path,
        manifest: dict[str, Any],
        questions_path: Path,
        selected_questions: list[dict[str, Any]],
        scale_factor: int,
    ) -> "FrozenGoldEvaluator":
        """Load every Gold file before any DB/provider/artifact action.

        The caller deliberately supplies only selected question records; this
        component rejects missing, duplicate, or mismatched identities instead
        of discovering a permissive fallback at runtime.
        """
        schema_path = root / "runner/contracts/gold-result.schema.json"
        schema = json.loads(schema_path.read_text())
        validator = Draft202012Validator(schema)
        expected_questions = {item["question_id"]: item for item in selected_questions}
        if set(gold_paths) != set(expected_questions):
            raise FrozenGoldError("Frozen Gold map must exactly cover selected question IDs")
        manifest_ref = _repo_relative(manifest_path, root)
        manifest_sha = _sha256(manifest_path)
        question_ref = _repo_relative(questions_path, root)
        question_sha = _sha256(questions_path)
        identities: dict[str, dict[str, Any]] = {}
        for question_id, configured_path in gold_paths.items():
            gold_path = (root / configured_path).resolve()
            if not gold_path.is_file():
                raise FrozenGoldError(f"Frozen Gold does not exist for {question_id}: {configured_path}")
            gold = json.loads(gold_path.read_text())
            errors = sorted(validator.iter_errors(gold), key=str)
            if errors:
                raise FrozenGoldError(f"Invalid frozen Gold for {question_id}: {errors[0].message}")
            question = expected_questions[question_id]
            if gold["question_id"] != question_id or gold["instance_id"] != question["instance_id"]:
                raise FrozenGoldError(f"Frozen Gold question identity mismatch for {question_id}")
            if gold["scale_factor"] != scale_factor:
                raise FrozenGoldError(f"Frozen Gold scale factor mismatch for {question_id}")
            dataset = gold["dataset"]
            if (
                dataset["manifest_path"] != manifest_ref
                or dataset["manifest_sha256"] != manifest_sha
                or dataset["dataset_sha256"] != manifest["dataset_sha256"]
                or dataset["database_sha256"] != manifest["database"]["sha256"]
            ):
                raise FrozenGoldError(f"Frozen Gold dataset identity mismatch for {question_id}")
            identity = gold["question_instance"]
            if identity["path"] != question_ref or identity["sha256"] != question_sha:
                raise FrozenGoldError(f"Frozen Gold question-instance identity mismatch for {question_id}")
            references = question["evaluator_only"]["reference_sql"]
            if len(references) != 1:
                raise FrozenGoldError(f"Frozen Gold runner requires exactly one reference SQL file for {question_id}")
            reference_path = (root / references[0]).resolve()
            if (
                gold["reference_sql"]["path"] != _repo_relative(reference_path, root)
                or gold["reference_sql"]["sha256"] != _sha256(reference_path)
            ):
                raise FrozenGoldError(f"Frozen Gold reference SQL identity mismatch for {question_id}")
            contract = question["evaluator_only"]["result_contract"]
            result = gold["result"]
            if result["columns"] != contract["columns"] or result["comparison"] != contract["comparison"]:
                raise FrozenGoldError(f"Frozen Gold result contract mismatch for {question_id}")
            identities[question_id] = gold
        return cls(identities)

    def evaluate(
        self,
        question_id: str,
        *,
        columns: list[str],
        row_count: int,
        result_sha256: str,
    ) -> FrozenEvaluation:
        started = perf_counter()
        try:
            expected = self._identities[question_id]["result"]
        except KeyError as exc:
            raise FrozenGoldError(f"No frozen Gold identity for {question_id}") from exc
        equivalent = (
            columns == expected["columns"]
            and row_count == expected["row_count"]
            and result_sha256 == expected["sha256"]
            and expected["normalization_revision"] == "canonical-json-v1"
        )
        return FrozenEvaluation(
            result_equivalent=equivalent,
            reference_result_sha256=expected["sha256"],
            duration_ms=(perf_counter() - started) * 1000,
        )
