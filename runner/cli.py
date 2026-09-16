from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from runner.core.agent import AgentTurn, AgentUsage, ScriptedAgentProvider, ToolCall
from runner.core.control_runner import run_control_experiment
from runner.core.pilot import run_representative_pilot


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
                        reasoning_tokens=usage.get("reasoning_tokens"),
                        provider_reported=bool(usage),
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
    pilot = subparsers.add_parser("run-pilot", help="Run the non-publishable q01 x 6 x 3 live pilot")
    pilot.add_argument("--root", type=Path, default=Path("."))
    pilot.add_argument("--output", type=Path, required=True)
    pilot.add_argument("--database-config", default="runner/config/database.yaml")
    pilot.add_argument("--instances", default="benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl")
    pilot.add_argument("--gold-pack", default="benchmark/tpcds/results/gold/sf1/representative-v1/pack.json")
    pilot.add_argument("--metricflow-runtime", type=Path, required=True)
    pilot.add_argument("--metricflow-executable", default="mf")
    pilot.add_argument("--skill-host-revision")
    live = subparsers.add_parser("run-live", help="Exploratory live run with readable SQL/result/Gold report")
    live.add_argument("--root", type=Path, default=Path("."))
    live.add_argument("--env-file", type=Path)
    live.add_argument("--output", type=Path)
    live.add_argument("--questions", nargs="+", default=["q01", "q02", "q03"])
    live.add_argument("--targets", nargs="+", choices=("blank_context", "ddl_only", "ossie", "okf", "skill", "metricflow"), default=["ddl_only"])
    live.add_argument("--repetitions", type=int, default=1)
    live.add_argument("--timeout", type=float, default=120)
    live.add_argument("--max-output-tokens", type=int, default=8192)
    live.add_argument("--max-turns", type=int, default=12)
    live.add_argument("--max-database-attempts", type=int, default=6)
    live.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate credentials, Gold, database, target artifacts and native runtimes without calling the model",
    )
    live.add_argument(
        "--strict-exit",
        action="store_true",
        help="Return nonzero when any trial is not correct; by default completed benchmark outcomes still return zero",
    )
    live.add_argument("--save-details", action="store_true", help="Save SQL and up to 5 result rows locally; never log hidden reasoning")
    live.add_argument("--database-config", default="runner/config/database.yaml")
    live.add_argument("--instances", default="benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl")
    live.add_argument("--gold-pack", default="benchmark/tpcds/results/gold/sf1/representative-v1/pack.json")
    live.add_argument("--metricflow-runtime", type=Path)
    live.add_argument("--metricflow-executable", default="mf")
    live.add_argument("--skill-host-revision")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-live":
        from runner.core.local_live import run_local_live
        try:
            return run_local_live(args)
        except (OSError, ValueError, RuntimeError) as error:
            print(f"run-live setup failed: {type(error).__name__}: {error}", file=sys.stderr)
            return 2
    if args.command == "run-control":
        run_record = run_control_experiment(
            args.config,
            _scripted_factory(args.script),
            root=args.root,
        )
        print(run_record)
        return 0
    if args.command == "run-pilot":
        manifest = run_representative_pilot(
            root=args.root,
            output_dir=args.output,
            database_config=args.database_config,
            instances_path=args.instances,
            gold_pack_path=args.gold_pack,
            metricflow_runtime_project_dir=args.metricflow_runtime,
            metricflow_executable=args.metricflow_executable,
            skill_host_revision=args.skill_host_revision,
        )
        print(manifest)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
