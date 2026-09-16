"""Curator/evaluator checks for public output requirements (never a target tool).

Only the rendered question goes to the agent. Contract metadata, SQL parsing,
and empty-schema binding stay on the curator/evaluator side of the boundary.
"""
from __future__ import annotations

import json
from datetime import date
import math
import re
from typing import Any


class QuestionContractError(ValueError):
    pass


def statement_contracts(instance: dict[str, Any]) -> list[dict[str, Any]]:
    contract = instance["evaluator_only"]["result_contract"]
    return contract["statements"] if "statements" in contract else [contract]


def render_output_requirements(contracts: list[dict[str, Any]]) -> str:
    """Render public instructions, not SQL, expected rows, hashes, or provenance."""
    count = len(contracts)
    lines = [f"Output requirements: submit exactly {count} result set(s) in the stated order."]
    for index, contract in enumerate(contracts, 1):
        lines.append(f"Result set {index}: return columns in this exact order, with these exact names: "
                     + ", ".join(contract["columns"]) + ".")
        keys = []
        for key in contract["order_by"]:
            name = key["column"]
            if "when" in key:
                condition = key["when"]
                name += f" (only when {condition['column']} = {condition['equals']}; otherwise NULL)"
            keys.append(f"{name} {key['direction']} NULLS {key['nulls']}")
        lines.append("Sort rows by " + ", ".join(keys) + ".")
        limit = contract["max_rows"]
        lines.append(f"Return up to {limit} rows." if limit is not None else "Return all matching rows; no row limit.")
    lines.append("Preserve duplicate rows unless the business rules above explicitly require deduplication. "
                 "Column names, column order, values, and row order must match these requirements; "
                 "canonical JSON serialization does not reorder columns or rows.")
    return " ".join(lines)


def validate_public_requirements(instance: dict[str, Any]) -> None:
    contracts = statement_contracts(instance)
    evaluator = instance["evaluator_only"]
    count = evaluator["expected_statement_count"]
    if len(contracts) != count or len(evaluator["reference_sql"]) != count:
        raise QuestionContractError("Reference, contract, and expected statement counts must agree")
    parameters = instance["orchestrator_only"]["parameters"]
    if len({parameter["name"] for parameter in parameters}) != len(parameters):
        raise QuestionContractError("Materialization parameter names must be unique")
    for parameter in parameters:
        value, kind = parameter["value"], parameter["type"]
        valid = {"integer": type(value) is int,
                 "number": type(value) is int or (type(value) is float and math.isfinite(value)),
                 "string": isinstance(value, str), "list": isinstance(value, list),
                 "identifier": isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)),
                 "date": False}
        if kind == "date" and isinstance(value, str):
            try:
                valid["date"] = date.fromisoformat(value).isoformat() == value
            except ValueError:
                pass
        if not valid[kind]:
            raise QuestionContractError(f"Materialization parameter {parameter['name']} must have type {kind}")
    for contract in contracts:
        for key in contract["order_by"]:
            if key["column"] not in contract["columns"] or (
                "when" in key and key["when"]["column"] not in contract["columns"]
            ):
                raise QuestionContractError("Sort keys must refer to declared output columns")
    if not instance["target_input"]["question"].endswith(render_output_requirements(contracts)):
        raise QuestionContractError("Question must include the complete public output requirements")


def _expression_identity(value: Any) -> Any:
    """Ignore locations/qualifiers, not sort directions, expressions, or values."""
    if isinstance(value, list):
        return [_expression_identity(item) for item in value]
    if isinstance(value, dict):
        result = {key: _expression_identity(item) for key, item in value.items()
                  if key not in {"query_location", "alias"}}
        if result.get("class") == "COLUMN_REF":
            result["column_names"] = result["column_names"][-1:]
        return result
    return value


def _sort_sql(key: dict[str, Any]) -> str:
    name = '"' + key["column"].replace('"', '""') + '"'
    if "when" in key:
        condition = key["when"]
        column = '"' + condition["column"].replace('"', '""') + '"'
        name = f"CASE WHEN {column} = {condition['equals']} THEN {name} END"
    return f"{name} {key['direction']} NULLS {key['nulls']}"


def _modifiers(database: Any, sql: str) -> list[dict[str, Any]]:
    parsed = json.loads(database.execute("SELECT json_serialize_sql(?)", [sql]).fetchone()[0])
    if parsed.get("error") or len(parsed.get("statements", [])) != 1:
        raise QuestionContractError("Reference must be exactly one parseable SELECT statement")
    node = parsed["statements"][0]["node"]
    # DuckDB represents materialized WITH clauses as wrapper nodes. Their own
    # modifiers are empty; the answer's outer modifiers belong to the child.
    while node["type"] == "CTE_NODE":
        node = node["child"]
    return node["modifiers"]


def validate_reference_contract(database: Any, sql: str, contract: dict[str, Any]) -> None:
    """Bind output columns and compare the outer ORDER BY/LIMIT with the contract.

    The caller supplies an empty physical schema. No SF1 results are read here.
    DuckDB 1.4.0 defaults are ASC and NULLS LAST; explicit clauses are preferred.
    """
    columns = list(database.sql(sql).limit(0).columns)
    if columns != contract["columns"]:
        raise QuestionContractError(f"Reference columns differ: {columns} != {contract['columns']}")
    actual = _modifiers(database, sql)
    expected = _modifiers(database, "SELECT 1 ORDER BY " + ", ".join(map(_sort_sql, contract["order_by"])))
    actual_order = next((item["orders"] for item in actual if item["type"] == "ORDER_MODIFIER"), [])
    expected_order = expected[0]["orders"]
    # ORDER BY ordinals (q49) name output positions, not literal sort constants.
    for key in actual_order:
        expression = key["expression"]
        position = expression.get("value", {}).get("value")
        if expression.get("class") == "CONSTANT" and type(position) is int and 1 <= position <= len(columns):
            key["expression"] = {"class": "COLUMN_REF", "type": "COLUMN_REF", "column_names": [columns[position - 1]]}

    def orders_identity(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"direction": "ASCENDING" if key["type"] == "ORDER_DEFAULT" else key["type"],
                 "nulls": "NULLS LAST" if key["null_order"] == "ORDER_DEFAULT" else key["null_order"],
                 "expression": _expression_identity(key["expression"])} for key in orders]

    if orders_identity(actual_order) != orders_identity(expected_order):
        raise QuestionContractError("Reference outer ORDER BY differs from the public contract")
    limits = [item for item in actual if item["type"] == "LIMIT_MODIFIER"]
    if contract["max_rows"] is None:
        if limits:
            raise QuestionContractError("Reference LIMIT differs from the unlimited public contract")
    elif len(limits) != 1 or limits[0]["offset"] is not None or (
        (limits[0].get("limit") or {}).get("value", {}).get("value") != contract["max_rows"]
    ):
        raise QuestionContractError("Reference LIMIT differs from the public contract")


def validate_result_contract(result: dict[str, Any], contract: dict[str, Any]) -> None:
    if result["columns"] != contract["columns"]:
        raise QuestionContractError("Gold columns differ from the declared result contract")
    if contract["max_rows"] is not None and result["row_count"] > contract["max_rows"]:
        raise QuestionContractError("Gold row count exceeds the declared result contract")
    if result["comparison"] != contract["comparison"] or result["order_sensitive"] != contract["order_sensitive"]:
        raise QuestionContractError("Gold comparison behavior differs from the declared result contract")
    if result["normalization_revision"] != "canonical-json-v1":
        raise QuestionContractError("Gold normalization revision differs from the strict JSON contract")
