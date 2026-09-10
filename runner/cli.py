from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runner.core.agent import AgentTurn, AgentUsage, ScriptedAgentProvider, ToolCall
from runner.core.control_runner import run_control_experiment


def _scripted_factory(script_path: Path):
    document = json.loads(script_path.read_text())
    if document.get("schema_version") != "0.1.0":
        raise ValueError("Unsupported scripted provider schema_version")

    def factory(target: str, repetition: int, question: dict[str, Any]) -> ScriptedAgentProvider:
        key = f"{question['instance_id']}:{target}:r{repetition:02d}"
        raw_turns = document.get("trials", {}).get(key)
        if raw_turns is None:
            raise ValueError(f"Script has no turns for trial: {key}")
        turns = []
        for index, raw in enumerate(raw_turns):
            calls = tuple(
                ToolCall(
                    id=str(call.get("id", f"call-{index + 1:03d}")),
                    name=str(call["name"]),
                    arguments=dict(call.get("arguments", {})),
                )
                for call in raw.get("tool_calls", [])
            )
            usage = raw.get("usage", {})
            turns.append(
                AgentTurn(
                    content=raw.get("content"),
                    tool_calls=calls,
                    usage=AgentUsage(
                        input_tokens=usage.get("input_tokens"),
                        output_tokens=usage.get("output_tokens"),
                        cached_input_tokens=usage.get("cached_input_tokens"),
                    ),
                    response_id=raw.get("response_id"),
                )
            )
        return ScriptedAgentProvider(turns)

    return factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semantic-benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)
    control = subparsers.add_parser("run-control", help="Run blank-context and DDL-only trials")
    control.add_argument("--config", default="runner/config/control-sf1-q01.yaml")
    control.add_argument("--provider", choices=("scripted",), default="scripted")
    control.add_argument("--script", type=Path, required=True)
    control.add_argument("--root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-control":
        run_record = run_control_experiment(
            args.config,
            _scripted_factory(args.script),
            root=args.root,
        )
        print(run_record)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
