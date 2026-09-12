# Native adapter boundary

Native semantic targets are integrated through `NativeAdapter`, a deliberately
closed target-specific boundary. It does **not** define a universal semantic
query API and it must never silently substitute direct SQL.

An adapter may expose only operations declared for its target in
`runner/config/targets.native.yaml`. The target receives a `TargetQuestion`
made solely from `target_input.question`; `orchestrator_only`,
`evaluator_only`, Gold-result identities, reference SQL, and canonical
mappings do not cross this boundary.

Every production adapter must:

- run target-specific preflight before the trial;
- expose original native tool names and request payloads;
- record sanitized request/response artifacts and durations;
- return `unsupported` rather than fallback when semantics are unavailable;
- reject evaluator-only paths, undeclared operations, and direct SQL where
  prohibited by the target registry.

The evaluator remains a separate component and is the only component allowed to
read Gold-result identities.
