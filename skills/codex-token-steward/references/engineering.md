# Engineering, context, and debugging

## Work contract

Extract required behavior, constraints, acceptance checks and unresolved risks from the task. Avoid another questionnaire if already clear. Retain this short contract through compaction and delegation. Do not trim necessary testing or architectural analysis to satisfy a token target.

## Explore in proportion to the decision

Use `rg`, symbol/reference tooling, dependency information, diffs and tests to narrow code first. Don't summarize the repository indiscriminately. A large repository does not automatically require a large model; small security/concurrency logic may.

Reuse a concise project map keyed to revision and validity conditions. Update affected areas after changes; never assume unchanged filenames mean unchanged dependencies/configuration. Avoid restarting a task purely due to context size: valuable context and cache may be lost. A deliberate handoff includes decisions, invariants, relevant paths, experiments, unresolved issues, revision and exact next step.

## Model routing and subagents

Keep the capable lead's understanding of the project when useful. For explicitly authorized delegation, a cheaper/different model may perform bounded read-only discovery, extraction, or well-defined implementation. Deterministic scripts/codemods are preferable when judgment is unnecessary. Routing must use models/settings actually available to the host; discovery alone does not prove suitability.

Account for worker execution + context briefing + coordination + lead verification + expected rework. Skip delegation when the lead already knows the answer, the assignment is tiny, or verifying it means repeating everything. Don't fork full history into every worker when a precise brief suffices. Don't parallelize dependent mutations or competing ownership of the same files. Use isolated checkouts when needed and include integration effort.

Evidence handoff: files/symbols and revision; focused excerpts or reproducible commands; facts versus interpretations; coverage and gaps; contradictions and uncertainty. Lead inspects critical evidence directly. Never treat a worker summary as proof that no other call paths exist.

## Debug with experiments

Maintain reproduction, observations, hypotheses, experiments/results, and changes. Each expensive action should reduce a relevant uncertainty or implement a supported fix. Repeated equivalent patches without a changing hypothesis are a signal to diagnose differently, not keep buying cheaper attempts.

Escalate capability/scope when failures persist, evidence conflicts, or hidden cross-system dependencies emerge. Apply user-authorized routing policy, otherwise recommend the change. Don't ask a weak worker to certify high-risk behavior beyond its evidence. Verify the integrated result and likely affected contracts, not just syntax.

## Reuse checks responsibly

Reuse completed validation only while relevant inputs/environment remain valid. Run targeted checks after narrow changes, then required integration/release checks. Broaden when the change affects shared infrastructure or new evidence warrants it. A passing test for another revision is not current proof. Review new differences rather than repeatedly reviewing unchanged work, while checking interactions.

## Explain the intervention briefly

Useful: “Reused the verified schema inventory; only the affected migration changed.”
Unsupported: “Saved 70% of tokens.” Never invent a counterfactual. Include any quality regression or extra corrective work in the outcome record.
