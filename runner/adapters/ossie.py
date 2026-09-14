"""Native Apache Ossie YAML consumer.

The adapter exposes the original Ossie document rather than translating it into
Skill, OKF, shared chunks, or any other normalized semantic-evidence format. It
validates the pinned Apache Ossie schema, checks local object references, indexes
native objects by type/name, and returns source slices taken directly from the
original YAML text.

The adapter deliberately does not own SQL execution. In the Ossie benchmark
condition, SQL is authored by the agent and executed by the separately declared
read-only DuckDB tool.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1, sha256
import json
from pathlib import Path, PurePosixPath
import re
from time import perf_counter
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from runner.core.native_adapter import (
    NativeAdapterError,
    NativeIsolationError,
    NativeOperationError,
    NativeRequest,
    NativeResponse,
    assert_declared_operation,
    assert_native_artifact_root,
)


OSSIE_SCHEMA_COMMIT = "c109cf5b0a06970a97599e8f7c2a72859822a3a4"
OSSIE_SCHEMA_BLOB_SHA = "4e50f1eeafd3c56c700e6c5482f9b356b34e1fee"
OSSIE_SCHEMA_RELATIVE_PATH = "core-spec/ossie-schema.json"
OSSIE_DOCUMENT_VERSION = "0.2.0.dev0"
OSSIE_DEFAULT_MODEL_FILE = "tpcds-sf1.yaml"
OSSIE_SCHEMA_FILE = Path(__file__).with_name("schemas") / "ossie-c109cf5-schema.json"

_OBJECT_TYPES = frozenset({"semantic_model", "dataset", "field", "relationship", "metric"})
_QUALIFIED_REFERENCE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")


class OssieConfigurationError(NativeAdapterError):
    """Raised when the local Ossie consumer is configured incorrectly."""


class OssieValidationError(NativeAdapterError):
    """Raised when the native Ossie document or its references are invalid."""


class OssiePreflightError(NativeAdapterError):
    """Raised when discovery/read is attempted before validation succeeds."""


@dataclass(frozen=True)
class OssieAccessEvent:
    """Sanitized telemetry for one Ossie operation.

    Raw YAML content is intentionally never retained in telemetry.
    """

    operation: str
    duration_ms: float
    object_type: str | None = None
    object_id: str | None = None
    byte_count: int | None = None
    artifact_sha256: str | None = None
    result_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _ObjectRef:
    object_type: str
    object_id: str
    qualified_id: str
    model_id: str
    dataset_id: str | None
    start: int
    end: int

    def metadata(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "object_type": self.object_type,
            "id": self.object_id,
            "qualified_id": self.qualified_id,
            "model_id": self.model_id,
        }
        if self.dataset_id is not None:
            value["dataset_id"] = self.dataset_id
        return value


def _sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    """Return the Git blob object id for exact bytes.

    OSSIE_SCHEMA_BLOB_SHA is the object id of the upstream schema blob at the
    pinned commit. Recomputing it from the vendored bytes proves that the local
    file is byte-for-byte identical to that upstream object instead of merely
    trusting telemetry metadata.
    """

    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def _artifact_id(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _mapping_value(node: MappingNode, key: str) -> Node | None:
    for key_node, value_node in node.value:
        if isinstance(key_node, ScalarNode) and key_node.value == key:
            return value_node
    return None


def _required_scalar(node: MappingNode, key: str, context: str) -> str:
    value = _mapping_value(node, key)
    if not isinstance(value, ScalarNode) or not value.value:
        raise OssieValidationError(f"{context} must contain a non-empty scalar {key!r}")
    return value.value


class OssieAdapter:
    """Closed consumer for one pinned native Apache Ossie YAML document."""

    version = "ossie-native-consumer-v0.1"

    _native_operations = frozenset(
        {
            "ossie.validate",
            "ossie.inspect_model",
            "ossie.read_native_yaml",
        }
    )

    def __init__(
        self,
        *,
        target_config: Mapping[str, Any],
        model_root: str | Path,
        schema_path: str | Path = OSSIE_SCHEMA_FILE,
    ) -> None:
        self._target_config = dict(target_config)
        self._root = Path(model_root)
        self._schema_path = Path(schema_path)
        self._ready = False
        self._closed = False
        self._events: list[OssieAccessEvent] = []
        self._raw_text: str | None = None
        self._document: dict[str, Any] | None = None
        self._yaml_root: Node | None = None
        self._index: dict[str, list[_ObjectRef]] = {kind: [] for kind in _OBJECT_TYPES}

        if self._target_config.get("role") != "semantic_interchange_specification":
            raise OssieConfigurationError("Ossie target must be a semantic_interchange_specification")
        surface = self._target_config.get("native_surface", {})
        if not isinstance(surface, Mapping) or surface.get("name") != "ossie_yaml_spec_consumer":
            raise OssieConfigurationError("Ossie target must declare ossie_yaml_spec_consumer")
        assert_native_artifact_root(surface.get("artifact_root"))

        pinned_commit = surface.get("schema_commit", surface.get("spec_revision"))
        if pinned_commit != OSSIE_SCHEMA_COMMIT:
            raise OssieConfigurationError(
                f"Ossie schema commit must be pinned to {OSSIE_SCHEMA_COMMIT}; found {pinned_commit!r}"
            )
        schema_blob = surface.get("schema_blob_sha")
        if schema_blob is not None and schema_blob != OSSIE_SCHEMA_BLOB_SHA:
            raise OssieConfigurationError(
                f"Ossie schema blob must be {OSSIE_SCHEMA_BLOB_SHA}; found {schema_blob!r}"
            )
        schema_relative_path = surface.get("schema_path")
        if schema_relative_path is not None and schema_relative_path != OSSIE_SCHEMA_RELATIVE_PATH:
            raise OssieConfigurationError(
                f"Ossie schema path must be {OSSIE_SCHEMA_RELATIVE_PATH}; found {schema_relative_path!r}"
            )

        model_file = surface.get("model_file", OSSIE_DEFAULT_MODEL_FILE)
        if not isinstance(model_file, str) or not model_file:
            raise OssieConfigurationError("native_surface.model_file must be a non-empty relative path")
        self._model_relative_path = self._normalize_relative_path(model_file)

        if self._root.is_symlink() or not self._root.is_dir():
            raise OssieConfigurationError("Ossie model root must be an existing non-symlink directory")
        self._resolved_root = self._root.resolve(strict=True)
        self._model_path = self._resolve_model_path(self._model_relative_path)

        if self._schema_path.is_symlink() or not self._schema_path.is_file():
            raise OssieConfigurationError("Pinned Ossie schema file is missing or is a symlink")

    def public_tools(self) -> Sequence[dict[str, Any]]:
        """Expose native discovery/read operations only.

        Schema validation is a preflight operation. ``db.execute_readonly`` and
        ``benchmark.submit_result`` are harness-owned operations and are not
        implemented by this adapter.
        """

        return (
            {
                "name": "ossie.inspect_model",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "object_type": {"type": "string", "enum": sorted(_OBJECT_TYPES)},
                        "object_id": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "ossie.read_native_yaml",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "object_type": {"type": "string", "enum": sorted(_OBJECT_TYPES)},
                        "object_id": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
        )

    def preflight(self, deadline_seconds: float) -> Sequence[NativeResponse]:
        self._ensure_open()
        self._validate_deadline(deadline_seconds)
        self._ready = False
        response = self._timed(
            "ossie.validate",
            lambda: self.validate(),
            {"operation": "ossie.validate", "schema_commit": OSSIE_SCHEMA_COMMIT},
        )
        self._ready = response.status == "succeeded"
        return (response,)

    def dispatch(self, request: NativeRequest) -> NativeResponse:
        self._ensure_open()
        self._validate_deadline(request.deadline_seconds)
        self._assert_declared_or_preflight_operation(request.operation)
        if request.operation not in self._native_operations:
            raise OssieConfigurationError(f"Ossie adapter does not own harness operation: {request.operation}")

        args = self._arguments(request.arguments)
        if request.operation == "ossie.validate":
            self._reject_extra(args, set())
            response = self._timed(
                request.operation,
                lambda: self.validate(),
                {"operation": request.operation},
            )
            self._ready = response.status == "succeeded"
            return response

        if not self._ready:
            raise OssiePreflightError("Ossie schema/reference validation must succeed before discovery or reads")

        if request.operation == "ossie.inspect_model":
            self._reject_extra(args, {"object_type", "object_id"})
            return self._timed(
                request.operation,
                lambda: self.inspect_model(
                    object_type=args.get("object_type"),
                    object_id=args.get("object_id"),
                ),
                {"operation": request.operation, **args},
            )
        if request.operation == "ossie.read_native_yaml":
            self._reject_extra(args, {"path", "object_type", "object_id"})
            return self._timed(
                request.operation,
                lambda: self.read_native_yaml(
                    path=args.get("path"),
                    object_type=args.get("object_type"),
                    object_id=args.get("object_id"),
                ),
                {"operation": request.operation, **args},
            )
        raise OssieConfigurationError(f"No Ossie operation mapping for {request.operation}")

    def close(self) -> None:
        self._closed = True
        self._ready = False
        self._raw_text = None
        self._document = None
        self._yaml_root = None
        self._index = {kind: [] for kind in _OBJECT_TYPES}

    def access_events(self) -> tuple[OssieAccessEvent, ...]:
        return tuple(self._events)

    def validate(self) -> dict[str, Any]:
        """Validate against the pinned official JSON schema and local references."""

        text = self._model_path.read_text(encoding="utf-8")
        try:
            document = yaml.safe_load(text)
            yaml_root = yaml.compose(text)
        except yaml.YAMLError as error:
            raise OssieValidationError(f"Invalid Ossie YAML: {self._model_relative_path}") from error
        if not isinstance(document, dict) or not isinstance(yaml_root, MappingNode):
            raise OssieValidationError("Ossie document must be a top-level mapping")

        schema_bytes = self._schema_path.read_bytes()
        actual_blob_sha = _git_blob_sha(schema_bytes)
        if actual_blob_sha != OSSIE_SCHEMA_BLOB_SHA:
            raise OssieValidationError(
                "Vendored Ossie schema bytes do not match the pinned upstream Git blob: "
                f"expected {OSSIE_SCHEMA_BLOB_SHA}, found {actual_blob_sha}"
            )
        schema_text = schema_bytes.decode("utf-8")
        try:
            schema = json.loads(schema_text)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(document)
        except (UnicodeDecodeError, json.JSONDecodeError, JsonSchemaValidationError) as error:
            raise OssieValidationError(f"Official Ossie schema validation failed: {error}") from error
        except Exception as error:
            if error.__class__.__module__.startswith("jsonschema"):
                raise OssieValidationError(f"Pinned Ossie schema is invalid: {error}") from error
            raise

        if document.get("version") != OSSIE_DOCUMENT_VERSION:
            raise OssieValidationError(
                f"Ossie document version must be {OSSIE_DOCUMENT_VERSION}; found {document.get('version')!r}"
            )

        counts = self._validate_references(document)
        index = self._build_source_index(yaml_root, text)
        indexed_counts = {kind: len(index[kind]) for kind in ("dataset", "field", "relationship", "metric")}
        if indexed_counts != counts:
            raise OssieValidationError(
                f"Parsed source index does not match validated object counts: {indexed_counts} != {counts}"
            )

        self._raw_text = text
        self._document = document
        self._yaml_root = yaml_root
        self._index = index

        return {
            "status": "ok",
            "source_path": self._model_relative_path,
            "version": OSSIE_DOCUMENT_VERSION,
            "schema_commit": OSSIE_SCHEMA_COMMIT,
            "schema_path": OSSIE_SCHEMA_RELATIVE_PATH,
            "schema_blob_sha": actual_blob_sha,
            "schema_sha256": sha256(schema_bytes).hexdigest(),
            "artifact_sha256": _sha256_text(text),
            "byte_count": len(text.encode("utf-8")),
            "counts": counts,
        }

    def inspect_model(self, *, object_type: Any = None, object_id: Any = None) -> dict[str, Any]:
        self._require_snapshot()
        normalized_type = self._normalize_object_type(object_type) if object_type is not None else None
        normalized_id = self._normalize_object_id(object_id) if object_id is not None else None
        if normalized_id is not None and normalized_type is None:
            raise OssieConfigurationError("object_id requires object_type")

        if normalized_type is not None and normalized_id is not None:
            ref = self._resolve_object(normalized_type, normalized_id)
            return {
                "source_path": self._model_relative_path,
                "object": ref.metadata(),
                "artifact_sha256": _sha256_text(self._raw_text or ""),
                "count": 1,
            }
        if normalized_type is not None:
            objects = [ref.metadata() for ref in self._index[normalized_type]]
            return {
                "source_path": self._model_relative_path,
                "object_type": normalized_type,
                "objects": objects,
                "count": len(objects),
                "artifact_sha256": _sha256_text(self._raw_text or ""),
            }

        counts = {kind: len(self._index[kind]) for kind in ("dataset", "field", "relationship", "metric")}
        models = [ref.metadata() for ref in self._index["semantic_model"]]
        return {
            "source_path": self._model_relative_path,
            "version": OSSIE_DOCUMENT_VERSION,
            "semantic_models": models,
            "counts": counts,
            "artifact_sha256": _sha256_text(self._raw_text or ""),
            "count": sum(counts.values()),
        }

    def read_native_yaml(
        self,
        *,
        path: Any = None,
        object_type: Any = None,
        object_id: Any = None,
    ) -> dict[str, Any]:
        """Return the full native YAML or one exact source slice from it."""

        text = self._require_snapshot()
        if path is not None:
            if not isinstance(path, str) or not path:
                raise OssieConfigurationError("path must be a non-empty string when provided")
            requested = self._normalize_relative_path(path)
            if requested != self._model_relative_path:
                raise NativeIsolationError("Ossie consumer may read only the declared native model YAML")
            self._resolve_model_path(requested)

        normalized_type = self._normalize_object_type(object_type) if object_type is not None else None
        normalized_id = self._normalize_object_id(object_id) if object_id is not None else None
        if (normalized_type is None) != (normalized_id is None):
            raise OssieConfigurationError("object_type and object_id must be provided together")

        if normalized_type is None:
            content = text
            return {
                "source_path": self._model_relative_path,
                "object_type": None,
                "object_id": None,
                "content": content,
                "byte_count": len(content.encode("utf-8")),
                "artifact_sha256": _sha256_text(content),
            }

        ref = self._resolve_object(normalized_type, normalized_id or "")
        content = text[ref.start : ref.end]
        return {
            "source_path": self._model_relative_path,
            "object_type": ref.object_type,
            "object_id": ref.object_id,
            "qualified_id": ref.qualified_id,
            "content": content,
            "byte_count": len(content.encode("utf-8")),
            "artifact_sha256": _sha256_text(content),
        }

    def _timed(self, operation: str, handler: Any, request_payload: Mapping[str, Any]) -> NativeResponse:
        started = perf_counter()
        output = handler()
        duration_ms = (perf_counter() - started) * 1000
        self._record_event(operation, duration_ms, output)
        response_identity: Mapping[str, Any]
        if isinstance(output.get("artifact_sha256"), str):
            response_identity = {
                "operation": operation,
                "artifact_sha256": output["artifact_sha256"],
                "object_type": output.get("object_type"),
                "object_id": output.get("object_id"),
            }
        else:
            response_identity = {"operation": operation, "status": output.get("status"), "count": output.get("count")}
        return NativeResponse(
            status="succeeded",
            duration_ms=duration_ms,
            output=output,
            request_artifact=_artifact_id(request_payload),
            response_artifact=_artifact_id(response_identity),
        )

    def _record_event(self, operation: str, duration_ms: float, output: Mapping[str, Any]) -> None:
        object_type = output.get("object_type") if isinstance(output.get("object_type"), str) else None
        object_id = output.get("object_id") if isinstance(output.get("object_id"), str) else None
        if object_type is None and isinstance(output.get("object"), Mapping):
            candidate = output["object"]
            object_type = candidate.get("object_type") if isinstance(candidate.get("object_type"), str) else None
            object_id = candidate.get("id") if isinstance(candidate.get("id"), str) else None
        byte_count = output.get("byte_count") if isinstance(output.get("byte_count"), int) else None
        artifact_hash = output.get("artifact_sha256") if isinstance(output.get("artifact_sha256"), str) else None
        result_count = output.get("count") if isinstance(output.get("count"), int) else None
        if result_count is None and isinstance(output.get("counts"), Mapping):
            values = [value for value in output["counts"].values() if isinstance(value, int)]
            result_count = sum(values)
        self._events.append(
            OssieAccessEvent(
                operation=operation,
                duration_ms=round(duration_ms, 3),
                object_type=object_type,
                object_id=object_id,
                byte_count=byte_count,
                artifact_sha256=artifact_hash,
                result_count=result_count,
            )
        )

    def _validate_references(self, document: Mapping[str, Any]) -> dict[str, int]:
        semantic_models = document.get("semantic_model")
        if not isinstance(semantic_models, list) or not semantic_models:
            raise OssieValidationError("semantic_model must contain at least one model")

        model_names: set[str] = set()
        totals = {"dataset": 0, "field": 0, "relationship": 0, "metric": 0}
        errors: list[str] = []

        for model in semantic_models:
            if not isinstance(model, Mapping):
                errors.append("semantic model must be an object")
                continue
            model_name = model.get("name")
            if not isinstance(model_name, str) or not model_name:
                errors.append("semantic model name must be non-empty")
                continue
            if model_name in model_names:
                errors.append(f"duplicate semantic model name: {model_name}")
            model_names.add(model_name)

            datasets = model.get("datasets", [])
            dataset_fields: dict[str, set[str]] = {}
            if not isinstance(datasets, list):
                errors.append(f"{model_name}: datasets must be a list")
                datasets = []
            for dataset in datasets:
                if not isinstance(dataset, Mapping):
                    errors.append(f"{model_name}: dataset must be an object")
                    continue
                dataset_name = dataset.get("name")
                if not isinstance(dataset_name, str) or not dataset_name:
                    errors.append(f"{model_name}: dataset name must be non-empty")
                    continue
                if dataset_name in dataset_fields:
                    errors.append(f"{model_name}: duplicate dataset {dataset_name}")
                    continue
                fields = dataset.get("fields", [])
                if not isinstance(fields, list):
                    errors.append(f"{model_name}.{dataset_name}: fields must be a list")
                    fields = []
                field_names: set[str] = set()
                for field in fields:
                    field_name = field.get("name") if isinstance(field, Mapping) else None
                    if not isinstance(field_name, str) or not field_name:
                        errors.append(f"{model_name}.{dataset_name}: field name must be non-empty")
                        continue
                    if field_name in field_names:
                        errors.append(f"{model_name}.{dataset_name}: duplicate field {field_name}")
                    field_names.add(field_name)
                dataset_fields[dataset_name] = field_names
                totals["dataset"] += 1
                totals["field"] += len(field_names)

                for key_name in ("primary_key",):
                    key_fields = dataset.get(key_name, [])
                    if isinstance(key_fields, list):
                        for field_name in key_fields:
                            if field_name not in field_names:
                                errors.append(
                                    f"{model_name}.{dataset_name}: {key_name} references unknown field {field_name}"
                                )
                unique_keys = dataset.get("unique_keys", [])
                if isinstance(unique_keys, list):
                    for key in unique_keys:
                        if isinstance(key, list):
                            for field_name in key:
                                if field_name not in field_names:
                                    errors.append(
                                        f"{model_name}.{dataset_name}: unique_keys references unknown field {field_name}"
                                    )

            relationships = model.get("relationships", []) or []
            relationship_names: set[str] = set()
            if not isinstance(relationships, list):
                errors.append(f"{model_name}: relationships must be a list")
                relationships = []
            for relationship in relationships:
                if not isinstance(relationship, Mapping):
                    errors.append(f"{model_name}: relationship must be an object")
                    continue
                relationship_name = relationship.get("name")
                if not isinstance(relationship_name, str) or not relationship_name:
                    errors.append(f"{model_name}: relationship name must be non-empty")
                    continue
                if relationship_name in relationship_names:
                    errors.append(f"{model_name}: duplicate relationship {relationship_name}")
                relationship_names.add(relationship_name)
                from_dataset = relationship.get("from")
                to_dataset = relationship.get("to")
                if from_dataset not in dataset_fields:
                    errors.append(f"{model_name}.{relationship_name}: unknown from dataset {from_dataset}")
                if to_dataset not in dataset_fields:
                    errors.append(f"{model_name}.{relationship_name}: unknown to dataset {to_dataset}")
                from_columns = relationship.get("from_columns", [])
                to_columns = relationship.get("to_columns", [])
                if isinstance(from_columns, list) and isinstance(to_columns, list) and len(from_columns) != len(to_columns):
                    errors.append(f"{model_name}.{relationship_name}: relationship column counts differ")
                if from_dataset in dataset_fields and isinstance(from_columns, list):
                    for field_name in from_columns:
                        if field_name not in dataset_fields[from_dataset]:
                            errors.append(
                                f"{model_name}.{relationship_name}: unknown field {from_dataset}.{field_name}"
                            )
                if to_dataset in dataset_fields and isinstance(to_columns, list):
                    for field_name in to_columns:
                        if field_name not in dataset_fields[to_dataset]:
                            errors.append(f"{model_name}.{relationship_name}: unknown field {to_dataset}.{field_name}")
            totals["relationship"] += len(relationship_names)

            metrics = model.get("metrics", []) or []
            metric_names: set[str] = set()
            if not isinstance(metrics, list):
                errors.append(f"{model_name}: metrics must be a list")
                metrics = []
            for metric in metrics:
                if not isinstance(metric, Mapping):
                    errors.append(f"{model_name}: metric must be an object")
                    continue
                metric_name = metric.get("name")
                if not isinstance(metric_name, str) or not metric_name:
                    errors.append(f"{model_name}: metric name must be non-empty")
                    continue
                if metric_name in metric_names:
                    errors.append(f"{model_name}: duplicate metric {metric_name}")
                metric_names.add(metric_name)
                expression = metric.get("expression", {})
                dialects = expression.get("dialects", []) if isinstance(expression, Mapping) else []
                for dialect_expression in dialects if isinstance(dialects, list) else []:
                    sql = dialect_expression.get("expression") if isinstance(dialect_expression, Mapping) else None
                    if not isinstance(sql, str):
                        continue
                    for dataset_name, field_name in _QUALIFIED_REFERENCE.findall(sql):
                        if dataset_name in dataset_fields and field_name not in dataset_fields[dataset_name]:
                            errors.append(
                                f"{model_name}.{metric_name}: expression references unknown field "
                                f"{dataset_name}.{field_name}"
                            )
            totals["metric"] += len(metric_names)

        if errors:
            preview = "; ".join(errors[:12])
            suffix = "" if len(errors) <= 12 else f"; ... {len(errors) - 12} more"
            raise OssieValidationError(f"Ossie object-reference validation failed: {preview}{suffix}")
        return totals

    def _build_source_index(self, yaml_root: MappingNode, text: str) -> dict[str, list[_ObjectRef]]:
        index: dict[str, list[_ObjectRef]] = {kind: [] for kind in _OBJECT_TYPES}
        models_node = _mapping_value(yaml_root, "semantic_model")
        if not isinstance(models_node, SequenceNode):
            raise OssieValidationError("semantic_model source node must be a sequence")

        for model_node in models_node.value:
            if not isinstance(model_node, MappingNode):
                raise OssieValidationError("semantic_model entries must be mappings")
            model_id = _required_scalar(model_node, "name", "semantic_model")
            index["semantic_model"].append(
                self._object_ref("semantic_model", model_id, model_id, model_id, None, model_node, text)
            )

            datasets_node = _mapping_value(model_node, "datasets")
            if isinstance(datasets_node, SequenceNode):
                for dataset_node in datasets_node.value:
                    if not isinstance(dataset_node, MappingNode):
                        continue
                    dataset_id = _required_scalar(dataset_node, "name", f"semantic_model {model_id}")
                    index["dataset"].append(
                        self._object_ref(
                            "dataset",
                            dataset_id,
                            f"{model_id}/{dataset_id}",
                            model_id,
                            dataset_id,
                            dataset_node,
                            text,
                        )
                    )
                    fields_node = _mapping_value(dataset_node, "fields")
                    if isinstance(fields_node, SequenceNode):
                        for field_node in fields_node.value:
                            if not isinstance(field_node, MappingNode):
                                continue
                            field_id = _required_scalar(field_node, "name", f"dataset {dataset_id}")
                            index["field"].append(
                                self._object_ref(
                                    "field",
                                    field_id,
                                    f"{model_id}/{dataset_id}/{field_id}",
                                    model_id,
                                    dataset_id,
                                    field_node,
                                    text,
                                )
                            )

            for object_type, key in (("relationship", "relationships"), ("metric", "metrics")):
                objects_node = _mapping_value(model_node, key)
                if not isinstance(objects_node, SequenceNode):
                    continue
                for object_node in objects_node.value:
                    if not isinstance(object_node, MappingNode):
                        continue
                    object_id = _required_scalar(object_node, "name", f"semantic_model {model_id}")
                    index[object_type].append(
                        self._object_ref(
                            object_type,
                            object_id,
                            f"{model_id}/{object_id}",
                            model_id,
                            None,
                            object_node,
                            text,
                        )
                    )
        return index

    def _object_ref(
        self,
        object_type: str,
        object_id: str,
        qualified_id: str,
        model_id: str,
        dataset_id: str | None,
        node: Node,
        text: str,
    ) -> _ObjectRef:
        start = node.start_mark.index
        line_start = text.rfind("\n", 0, start) + 1
        end = node.end_mark.index
        if end < len(text):
            next_newline = text.find("\n", end)
            end = len(text) if next_newline == -1 else next_newline + 1
        return _ObjectRef(
            object_type=object_type,
            object_id=object_id,
            qualified_id=qualified_id,
            model_id=model_id,
            dataset_id=dataset_id,
            start=line_start,
            end=end,
        )

    def _resolve_object(self, object_type: str, object_id: str) -> _ObjectRef:
        matches = [
            ref
            for ref in self._index[object_type]
            if ref.object_id == object_id or ref.qualified_id == object_id
        ]
        if not matches:
            raise OssieConfigurationError(f"Unknown Ossie {object_type} id: {object_id}")
        if len(matches) > 1:
            qualified = ", ".join(ref.qualified_id for ref in matches[:10])
            raise OssieConfigurationError(
                f"Ambiguous Ossie {object_type} id {object_id!r}; use qualified_id: {qualified}"
            )
        return matches[0]

    def _resolve_model_path(self, relative_path: str) -> Path:
        normalized = self._normalize_relative_path(relative_path)
        candidate = self._root.joinpath(*PurePosixPath(normalized).parts)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise OssieConfigurationError(f"Ossie model file does not exist: {normalized}") from error
        if not resolved.is_relative_to(self._resolved_root):
            raise NativeIsolationError("Ossie path resolves outside the declared model root")
        probe = candidate
        while probe != self._root.parent:
            if probe.is_symlink():
                raise NativeIsolationError("Symlinks are forbidden in Ossie model paths")
            if probe == self._root:
                break
            probe = probe.parent
        if not resolved.is_file() or resolved.suffix.lower() not in {".yaml", ".yml"}:
            raise OssieConfigurationError("Ossie model path must be a regular YAML file")
        return resolved

    @staticmethod
    def _normalize_relative_path(raw_path: str) -> str:
        normalized = raw_path.replace("\\", "/")
        pure = PurePosixPath(normalized)
        if not normalized or pure.is_absolute() or ".." in pure.parts or normalized.startswith("/"):
            raise NativeIsolationError("Ossie paths must remain inside the declared model root")
        return pure.as_posix()

    def _assert_declared_or_preflight_operation(self, operation: str) -> None:
        preflight = set(self._target_config.get("preflight_operations", []))
        if operation in preflight:
            if operation != "ossie.validate":
                raise NativeOperationError(f"Undeclared Ossie preflight operation: {operation}")
            return
        assert_declared_operation(self._target_config, operation)

    def _require_snapshot(self) -> str:
        if not self._ready or self._raw_text is None:
            raise OssiePreflightError("Ossie validation must succeed before reading the native document")
        return self._raw_text

    def _ensure_open(self) -> None:
        if self._closed:
            raise OssiePreflightError("Ossie adapter is closed")

    @staticmethod
    def _validate_deadline(deadline_seconds: float) -> None:
        if not isinstance(deadline_seconds, (int, float)) or isinstance(deadline_seconds, bool) or deadline_seconds <= 0:
            raise OssieConfigurationError("deadline_seconds must be positive")

    @staticmethod
    def _arguments(arguments: Any) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise OssieConfigurationError("Ossie operation arguments must be an object")
        return dict(arguments)

    @staticmethod
    def _reject_extra(arguments: Mapping[str, Any], allowed: set[str]) -> None:
        extra = sorted(set(arguments) - allowed)
        if extra:
            raise OssieConfigurationError(f"Unsupported Ossie arguments: {extra}")

    @staticmethod
    def _normalize_object_type(value: Any) -> str:
        if not isinstance(value, str) or value not in _OBJECT_TYPES:
            raise OssieConfigurationError(f"object_type must be one of {sorted(_OBJECT_TYPES)}")
        return value

    @staticmethod
    def _normalize_object_id(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise OssieConfigurationError("object_id must be a non-empty string")
        return value.strip()
