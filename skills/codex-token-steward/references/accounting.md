# Accounting contract and limitations

The collector is Python 3.9+ standard library only. It opens rollout files read-only and stores metadata in its own SQLite database. It never opens authentication files or the host's private databases. Paths for incremental cursors remain local; project identifiers and tool argument signatures are keyed hashes. Raw prompts, responses, tool arguments/results and credentials are not persisted. Tool output byte counts are not token estimates. Explicit notes may contain user-supplied sensitive facts.

## Counter semantics

- Input includes cached input; output includes reasoning output. Total is input + output.
- A changed cumulative usage event with `last_token_usage` is a recorded model-call observation. Unchanged totals are ignored.
- A cumulative delta without last-call detail is marked aggregate: it may span more than one request.
- Initial cumulative values without last-call detail are excluded, not attributed to a new call.
- Forked histories before the child's creation/history ordinal are excluded. Copied metadata cannot replace the owning session.
- Stable event identities deduplicate reingestion; file cursors allow incremental processing.
- Partial trailing lines are deferred. Invalid complete records are counted as coverage errors.
- Rewritten sources trigger a warning; rescan deduplicates matching identities but cannot prove arbitrary rewritten histories have identical semantics.

This adapter supports observed Codex rollout formats, not a stable public accounting API. Unknown fields can be ignored; missing essential usage fields must be disclosed. Tests include synthetic edge cases and installation/CLI behavior. New versions may require adapter updates.

## Message and child attribution

A message report represents an observed Codex turn ID, not each visible assistant text fragment or each user keystroke. A user turn can include many model calls/tool calls. Root-turn identifiers link child usage to the parent report. Without explicit root linkage, don't invent attribution from overlapping timestamps; session/audit totals can still include those calls. Concurrent tasks share account limits but their allowance deltas are not individual bills.

The current pre-final report cannot include the text the model has not generated yet. Stop runs after response generation but transcripts may flush later. Reports always carry a recorded-through time, status, and coverage. Next-prompt collection reconciles the preceding completed turn. Late child events may require a subsequent report refresh. The saved JSON is authoritative for that snapshot; a previously displayed footer cannot be retroactively corrected by this skill.

## Starting and ending usage

Each report includes `boundaries`: the cumulative recorded main-agent token ledger before/after the turn, and observed allowance snapshots with used/remaining percentages. Allowance starts use the most recent same-session reading at or before the turn, with its timestamp and age. If none exists, the first in-turn reading is explicitly marked approximate. Ending allowance uses the last reading observed during the turn; no reading means unavailable, not carry-forward. Only unchanged windows with nondecreasing usage receive percentage-point deltas. A reset/adjustment makes consumption delta unavailable. Other tasks can consume the same account allowance; these are not per-task bills. Standard 5-hour/weekly windows absent from available data are explicitly listed as unavailable. The collector does not call a live account API or add model turns to acquire these readings.

## Models and prices

Record exact observed model, effort and service tier; absent values remain unknown. No token-to-allowance conversion is assumed. The bundled registry has no prices. Imported rates need official source, checked date, effective interval, exact model/service and units. Rates older than 14 days are marked stale and not applied. Pricing is an estimate, not invoiced credit use. Never apply public API USD pricing as subscription costs. See models.md.

## Coverage and overhead

By default `collect` discovers local sessions/archives modified in the last 30 days; it reads available history within those selected files. `audit --days` filters by event timestamp. Cloud/other devices and missing files are outside coverage. Hook scans have a 12 MiB work budget, deferring remaining bytes with a warning; an explicit collection can finish indexing. Discovery itself inspects session headers and is not a constant-time operation.

Reports expose scan bytes/time, hook runtime and identified steward tool invocations. Exact model-token overhead attributable to the skill is unavailable because shared instructions/cache/context affect entire requests. Do not call collector CPU time “zero total overhead.” It does make zero direct model requests.

## Heuristics

Repeated keyed tool signatures, large context, explicit error markers, large outputs, computer-use volume, coordination calls and project/model baseline deviations flag investigation opportunities. They cannot establish wasted tokens, causal savings, correctness or acceptance. Dynamic orchestration inside one wrapper call is not a complete record of all nested operations. Review relevant evidence and project state before intervening.
