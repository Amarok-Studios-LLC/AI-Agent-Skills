# AI Agent Skills

Practical, inspectable agent skills from Amarok Studios LLC. Each skill lives in its own directory and can be installed independently.

| Skill | Purpose |
|---|---|
| [Codex Token Steward](skills/codex-token-steward/SKILL.md) | Measure usage per message/model call, investigate expensive workflows, and improve efficiency while preserving outcomes. |

## Codex Token Steward

Token Steward combines a concise agent skill with a local Python accounting engine. It helps answer **where did the allowance go, was the work necessary, and what can improve without lowering quality?**

It provides:

- Incremental usage collection from local Codex session records, with fork/duplicate handling and coverage diagnostics.
- Per-turn JSON/Markdown reports, individual recorded model calls, tool activity, cached input and reasoning subsets, and explicitly linked subagent usage.
- Starting/ending task token ledgers and allowance readings, with used/remaining percentages, timestamps, baseline age, and reset-aware changes.
- Compact per-response snapshots, optional lifecycle reporting, and short feedback for the next message.
- Weekly reset timing, suggested daily allowance pace, recent observed pace and conditional run-out estimates with explicit stale/sparse-data limits.
- Cross-shell Windows hook launchers, recorded handler failures, and real host-dispatch verification using a local canned response with no model inference.
- A `prepare` fallback for hosts that have not reloaded hooks, plus a direct local `status` command/Windows shortcut that needs no AI conversation.
- Personalization through project/model baselines, project facts, reversible interventions and explicitly accepted outcome comparisons.
- Guidance for context management, code changes, debugging, tool use, authorized multi-model delegation, deployments, backups and MySQL.
- A functional local artifact-manifest/delta planner for deployment preparation.
- Unknown-model tracking and an importable, sourced, versioned rate registry. Unknown prices stay unknown.

**Default: preserve the user's chosen capability and required checks.** High consumption is not automatically waste. The skill does not silently change models, skip tests, spawn agents, rewrite settings, or remove backup requirements to improve a token number.

## Install globally

Requires Python 3.9+; no third-party packages, API key, or paid service is needed by the collector.

Ask Codex to install `skills/codex-token-steward` from this repository using Skill Installer, or clone and install locally:

```sh
git clone https://github.com/Amarok-Studios-LLC/AI-Agent-Skills.git
cd AI-Agent-Skills
python install.py
```

Use `python3` if that is your Python command. The destination is `$CODEX_HOME/skills/codex-token-steward` or `~/.codex/skills/codex-token-steward`. The skill is available on the next turn. Invoke it with `$codex-token-steward`.

For global per-message reporting, opt into integration:

```sh
python install.py --integrate
```

The installer merges marked user-level instructions and three command hooks. It preserves other instructions/hooks, saves originals, and does not change model settings or hook trust. Existing identical skill files are accepted; use `--upgrade` to replace a previously installed, identified copy.

**Review and trust the hooks in Codex's hook controls (`/hooks` in CLI), then start a new task/reload configuration.** Hook definitions require host trust. A globally installed instruction block supplies a behavioral fallback if hooks are unavailable. See [integration and removal](skills/codex-token-steward/references/integration.md).

## Use

Natural-language examples:

- “Use $codex-token-steward to explain my usage this week.”
- “Keep my selected model and quality requirements, but avoid redundant work and report this message's usage.”
- “Investigate whether these deployment backups add recovery coverage.”
- “Compare the accepted outcomes before and after this optimization.”

Direct commands (replace `<skill>` with the installed directory):

```text
python <skill>/scripts/steward.py doctor
python <skill>/scripts/steward.py verify-host --codex-exe <absolute-Codex-executable>
python <skill>/scripts/steward.py status --refresh
python <skill>/scripts/steward.py prepare --current
python <skill>/scripts/steward.py collect --days 30
python <skill>/scripts/steward.py report --current --refresh --compact
python <skill>/scripts/steward.py audit --days 7 --refresh
python <skill>/scripts/steward.py policy --mode preserve-capability
python <skill>/scripts/steward.py models
python <skill>/scripts/steward.py notes --project <project-root>
```

`--current` needs Codex's current-session environment variable. Outside Codex, pass `--session <id>`. Global options (`--codex-home`, `--data-dir`) precede the subcommand. `--help` describes every command.

The collector stores derived metadata and reports in `$CODEX_STEWARD_HOME` or `$CODEX_HOME/token-steward`. JSON reports contain detailed per-call analysis; Markdown reports provide readable summaries. Notes and comparisons are documented in [personalization](skills/codex-token-steward/references/personalization.md).

`verify-host` checks actual UserPromptSubmit/Stop dispatch through an ephemeral host session backed by a local canned response, with no model inference. It requires already-trusted hooks and does not edit trust. Its result is tied to installed scripts/configuration and identifies the tested host. It does not certify that every existing desktop task has reloaded hooks, or test subagent dispatch. `prepare` provides the same prior-turn feedback when hook guidance is absent without recording a fake hook run.

## Simple conversation and zero-model-token checks

Use Codex normally for work requiring files, tools or task context. General conversation can be started directly in ChatGPT Chat, subject to its plan limits. The skill cannot make an AI reply token-free or silently reroute a message that Codex is already processing. See [routing boundaries](skills/codex-token-steward/references/routing.md).

For deterministic usage checks without any AI model call, run `status --refresh` directly. On Windows, double-click `Token Steward Status.cmd` in the data directory after integration. Asking Codex to run that same command still consumes tokens for the surrounding model turn. The status view uses local historical records, not live account billing.

## Report timing and honest limits

The footer generated before an assistant's final response **cannot include that not-yet-generated response**. It is labeled a snapshot. Stop hooks save post-response recorded usage; the next message reconciles the previous completed turn when records have flushed. The skill never forces another model turn to finish its own accounting.

Start/end allowance values use readings already present in the session logs. A prior reading carries its age; if only an in-turn reading exists, it is explicitly labeled as the first observation rather than an exact starting balance. Missing endpoints remain unavailable. Resets or decreasing readings suppress a misleading consumption delta. Unchanged rounded percentages do not mean zero consumption. The main-agent token ledger is cumulative recorded usage in that task, not a remaining token allocation; linked child consumption is reported separately.

Local logs are not an authoritative bill or complete cross-device/cloud record. Token counts, allowance percentages, API dollars and purchased credits are separate. Published rate estimates are optional and never substitute for billed amounts. Prices are deliberately not bundled: import current, sourced rates for the exact service tier and billing context. Unknown tiers/models/rates remain unpriced.

The rollout format is an internal interface that may change. Unsupported records, partial writes and missing coverage are disclosed. Model calls are recorded usage observations; aggregate-only events are marked. Root-linked children are included; unknown linkage is not guessed.

This release is not a hard spending firewall, remote deployment client, SQL executor, automatic model switcher, or always-on daemon. It provides accounting, analysis, executable local helpers, and guidance for tools the host already supports. No guaranteed savings percentage is claimed.

## Privacy and overhead

The collector makes no network or model requests. It stores counters, timestamps, model/tool identifiers, keyed tool-input signatures, local cursors and hashed project identifiers. It does not store transcript text, prompts, tool arguments/results, or credentials. Deliberately authored project notes can contain sensitive information; keep them local. Reports can still reveal activity and model/session identifiers; review before sharing.

Initial indexing can read substantial history. Later processing is incremental; hook scans are bounded. Reports disclose scan and hook overhead. The skill's instructions and reports still consume context, so it uses concise feedback and loads detailed references only when needed.

## Validation and contributing

```sh
python -m unittest discover -s tests -v
```

Tests use synthetic records and temporary directories. CI runs the suite on Windows, macOS and Linux. See [CONTRIBUTING.md](CONTRIBUTING.md) for compatibility, privacy and behavior requirements. Benchmarks must include acceptance quality, rework and overhead—not just lower token counts.

Licensed under [MIT](LICENSE). This community project is not an official OpenAI product.
