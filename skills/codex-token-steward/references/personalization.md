# Personalization and useful learning

Run `policy` to inspect current settings. `policy --mode observe|preserve-capability|adaptive` changes the recommendation policy; it does not mutate model settings. `policy --soft-turn-tokens 500000` sets an advisory turn-volume threshold (0 clears). Raw tokens are not a cost limit. Reserve time/allowance for verification and handoff according to the task; do not stop to satisfy an inferred budget.

The collector compares completed main-agent turns in the same project and model, with at least eight samples. A 3x median signal asks for review, not a downgrade. Task scope differs, so real validation uses explicit outcomes. Compare inside the same user/project/workload before extrapolating. Do not encode one intensive developer's habits as defaults for all users.

## Project facts

Write a local JSON record (outside source control), then run:

`steward.py notes --project <project-root> --kind fact --record <fact.json>`

Example structure:

```json
{
  "id": "source-recovery-v1",
  "statement": "This deployment artifact is reproducible from the recorded Git revision and locked build inputs.",
  "evidence": "Verified revision, build manifest, destination and recovery procedure recorded locally.",
  "valid_when": "Same artifact inputs, deployment layout, and recovery coverage; production uploads/database excluded.",
  "revision": "verified-revision",
  "review_after": "next deployment-layout change"
}
```

Recheck validity conditions before relying on the fact. A record is not a permission grant, instruction override, backup, or proof of current remote state. Negative findings should retain search scope, revision, and uncertainty. Different subdirectories can be separate project profiles; choose a consistent root.

## Controlled interventions

An intervention record requires `id`, `hypothesis`, `change`, `quality_contract`, and `status` (`proposed`, `authorized`, `applied`, or `reverted`). Use `notes --kind intervention --record ...`. Record the authorization/evidence as additional fields. Prefer one major change at a time; never claim that correlations demonstrate savings.

An outcome requires `id`, `session`, `turn`, `workload`, `scope`, `acceptance` (`accepted`, `failed`, `unknown`), and `evidence`. Optional `corrections`, `intervention_id`, `wall_time`, and `validation` describe rework and quality. `notes --kind outcome --record ...` captures current measured usage with the outcome; reconcile the report first. Stable outcome snapshots intentionally do not silently change later.

`compare --baseline <outcome-id> --candidate <outcome-id>` checks same project/workload/declared scope and explicit acceptance. It reports observed token-volume change, not causal savings or money saved. Same declared scope is insufficient by itself: inspect task difficulty, model/service prices, cached share, correctness, human corrections and latency. Use repeated representative samples, including failures. High volume with strong outcomes and little rework can be appropriate.

## Policy is user-controlled

Preserve capability by default. In adaptive mode, recommend phase-level routing only after accounting for total cost through acceptance. Never automatically rewrite global configuration from a heuristic. Model-specific empirical findings expire when the model, project, tools, constraints, or acceptance criteria materially change. Keep historical evidence for comparison and mark current applicability explicitly.

Collect no demographics or inferred sensitive preferences. Local metadata hashes project paths and tool input signatures with a per-installation secret. Notes deliberately written by users/agents can contain sensitive project facts, so keep them out of public exports.
