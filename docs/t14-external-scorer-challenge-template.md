# T14 external scorer challenge packet template

**State:** preparation only; no external challenge or independent evidence is recorded.

The challenger must be external to the preparation agents and must receive immutable,
content-addressed task, scorer, renderer, and judge versions. Agents may assemble and
mechanically validate the packet but may not invent a challenger identity or submission.

```yaml
schema_version: "1.0.0"
challenge_id: "<ID>"
repository_commit: "<40_HEX>"
task_commitment_sha256: "<64_HEX>"
scorer_commitment_sha256: "<64_HEX>"
renderer_commitment_sha256: "<64_HEX>"
judge_commitment_sha256: "<64_HEX>"
challenge_rules_sha256: "<64_HEX>"
challenger_identity: null
independence_declaration: null
submission_archive_sha256: null
immutable_command_log_sha256: null
result_manifest_sha256: null
failures_manifest_sha256: null
finding_dispositions_sha256: null
challenger_acknowledgement_sha256: null
agent_validation: "incomplete"
gate_effect: "none-until-steward-review"
```

Retain high-scoring invalid repairs, low-scoring valid repairs, preservation/locality
attacks, renderer disagreements, resource failures, and every unsuccessful attempt.
Critical findings block promotion. Any score-affecting repair requires a new scorer version,
frozen bridge set, paired old/new evidence, migration note, and fresh explicit decision.
