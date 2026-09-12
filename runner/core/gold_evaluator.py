from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


NORMALIZATION_REVISION = "canonical-json-v1"


class GoldIdentityError(ValueError):
    """A frozen Gold artifact is missing or does not match this evaluation."""


@dataclass(frozen=True)
class CandidateResultIdentity:
    columns: tuple[str, ...]
    row_count: int
    sha256: str
    normalization_revision: str = NORMALIZATION_REVISION


@dataclass(frozen=True)
class GoldEvaluation:
    result_equivalent: bool
    reference_result_sha256: str
    gold_result_sha256: str
    normalization_revision: str
    duration_ms: float


def _checksum(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GoldIdentityError(f"Expected JSON object: {path}")
    return value


class FrozenGoldEvaluator:
    """Evaluator-only comparison of a candidate identity against frozen Gold.

    This component accepts no SQL and no result rows. Callers must construct it
    outside the target/provider boundary and must not pass its path to a target.
    """

    def __init__(
        self,
        gold_path: str | Path,
        *,
        manifest_path: str | Path,
        question_instances_path: str | Path,
        reference_sql_path: str | Path,
        root: str | Path = ".",
    ):
        self.root = Path(root).resolve()
        self.gold_path = self._within_root(gold_path, "Gold result")
        self.manifest_path = self._within_root(manifest_path, "dataset manifest")
        self.question_instances_path = self._within_root(question_instances_path, "question instances")
        self.reference_sql_path = self._within_root(reference_sql_path, "reference SQL")
        self.gold = _load_json(self.gold_path)
        schema = _load_json(Path(__file__).resolve().parents[1] / "contracts/gold-result.schema.json")
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(self.gold)
        self._validate_identities()

    def _within_root(self, value: str | Path, label: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.root / path
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise GoldIdentityError(f"{label} must remain inside the repository root")
        return resolved

    def _validate_identities(self) -> None:
        dataset = self.gold["dataset"]
        if _checksum(self.manifest_path) != dataset["manifest_sha256"]:
            raise GoldIdentityError("Gold dataset manifest SHA-256 does not match")
        manifest = _load_json(self.manifest_path)
        if manifest["dataset_sha256"] != dataset["dataset_sha256"]:
            raise GoldIdentityError("Gold logical dataset SHA-256 does not match")
        if manifest["database"]["sha256"] != dataset["database_sha256"]:
            raise GoldIdentityError("Gold database SHA-256 does not match")
        if _checksum(self.question_instances_path) != self.gold["question_instance"]["sha256"]:
            raise GoldIdentityError("Gold question-instance SHA-256 does not match")
        if _checksum(self.reference_sql_path) != self.gold["reference_sql"]["sha256"]:
            raise GoldIdentityError("Gold reference SQL SHA-256 does not match")

    def evaluate(self, candidate: CandidateResultIdentity) -> GoldEvaluation:
        started = perf_counter()
        result = self.gold["result"]
        if candidate.normalization_revision != result["normalization_revision"]:
            raise GoldIdentityError("Candidate normalization revision does not match Gold")
        equivalent = (
            list(candidate.columns) == result["columns"]
            and candidate.row_count == result["row_count"]
            and candidate.sha256 == result["sha256"]
        )
        return GoldEvaluation(
            result_equivalent=equivalent,
            reference_result_sha256=result["sha256"],
            gold_result_sha256=_checksum(self.gold_path),
            normalization_revision=result["normalization_revision"],
            duration_ms=(perf_counter() - started) * 1000,
        )
