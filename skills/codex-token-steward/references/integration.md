# Install and integration

Install this skill globally with Codex's Skill Installer from `Amarok-Studios-LLC/AI-Agent-Skills`, path `skills/codex-token-steward`, or use the repository's local `install.py`. It is available on the next turn; a new task may be needed to load changed global instructions/configuration.

Optional global per-message integration:

`python <installed-skill>/scripts/steward.py install-integration`

This merges three user-level command hooks (`UserPromptSubmit`, `Stop`, `SubagentStop`) into `CODEX_HOME/hooks.json` and a marked reporting block into `CODEX_HOME/AGENTS.md`. It preserves other hooks/instructions and saves originals locally. It does not edit config.toml, model preferences, permissions or trust records.

**Codex requires review/trust of non-managed hook definitions.** Review them in the host's hook controls (`/hooks` in Codex CLI). Changed definitions may require another review. Do not bypass trust, edit trust databases, or claim configuration alone activates hooks. This is a host requirement documented at https://learn.chatgpt.com/docs/hooks .

## How reporting works

- Global instructions request one compact report near the end of each response, with measured usage so far and one relevant observation. This is a behavioral fallback, not hard enforcement.
- UserPromptSubmit collects recent available records, reconciles the preceding completed turn and supplies short, deterministic advice. It never includes transcript text.
- Stop saves a JSON/Markdown per-turn report and surfaces a `systemMessage` with the snapshot/report path. Host presentation varies; this does not rewrite the final assistant message.
- SubagentStop updates the parent's root-linked usage where available.
- Hooks never launch model calls, block completion, approve permissions, or request a continuation. No recursive reporting loop.

The final response cannot report its own exact token count before it exists. Always label pre-final snapshots and late-record reconciliation. Users can run `report --session ID --turn ID --refresh` later for the latest recorded view. Per-call analysis is in the JSON; do not print thousands of rows into chat.

## Diagnose

`doctor` reports configured integration and observed hook events separately. Successful manually simulated hook events prove handler behavior, not automatic host execution. Verify a real next turn before claiming automatic reporting works. For initial indexing use `collect --days 30`; subsequent collection is incremental. Unsupported transcript schemas, missing environment IDs, permissions, or host restrictions should produce a clear coverage limitation rather than fabricated zeroes.

Windows command hooks use a quoted native executable command. If a particular client uses a different shell contract, inspect its hook error and adjust only the command formatting; test with a synthetic event before trusting. macOS/Linux use shell-quoted executable and script paths. Python must remain at the recorded path; reinstall integration after moving runtimes/skill locations.

## Disable/remove

`remove-integration` removes only marked global instructions and handlers whose status marker is `codex-token-steward`. Other hooks and instructions remain. Analytics are retained. `policy --report-every-message no` suppresses Stop UI messages and makes the installed global command print a disabled notice instead of collecting/printing a footer. Hooks still collect and provide analysis; remove integration to disable those too. A direct `report` request remains available.

To uninstall the skill, remove integration first, then remove only its installed skill directory using normal filesystem tools. Delete the dedicated data directory separately only if the user explicitly wants to erase history. No automatic recursive deletion is shipped.

## Capability boundary

This release provides accounting, diagnostics, compact feedback, project facts, comparison records, model registry maintenance, and local deployment planning. It does not provide a universal hard spending cap, guaranteed cost savings, automatic background billing access, autonomous model switching, remote deployment/database execution, or an always-on daemon. The skill guides authorized execution using available host tools.
