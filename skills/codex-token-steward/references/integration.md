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

`doctor` separates configured hooks, handler observations, session-specific observations and verified host dispatch. A manually simulated hook event never proves host dispatch. Handler failures record only the error class, without input or exception text. For initial indexing use `collect --days 30`; subsequent collection is incremental.

After reviewing/trusting the hooks, run:

`python <skill>/scripts/steward.py verify-host --codex-exe <absolute-Codex-executable>`

This opt-in check launches the real app-server with an ephemeral session and a local canned Responses server. It checks that all three hooks are trusted, then correlates the host's completed UserPromptSubmit/Stop notifications with the collector's session-specific records. It makes no AI inference calls, changes no persistent model settings, and does not approve hooks. Host startup may perform its usual plugin/service initialization. The fixture consumes request bytes locally without retaining them. It never sends context to a model endpoint. No synthetic usage is saved to rollout history. SubagentStop dispatch is not exercised; test its handler separately rather than spawning an unnecessary agent.

The result is stored locally as `host-verification.json`. Changing scripts, hook definitions, or config invalidates the evidence. Verification covers that tested host, not every device or an already-running desktop session. If a desktop task has no hook guidance, use `prepare --current` once with its first substantive tool call; the global instruction fallback enables this automatically. Reload/start a task to load changed configuration; do not restart an active user's task without coordinating it. Missing usage stays unavailable.

Windows hooks use a PowerShell encoded invocation that works when dispatched by either cmd.exe or PowerShell. The encoding protects literal executable/argument paths; it is not encryption and contains no secrets. A quoted executable path alone is not valid PowerShell. No execution-policy bypass is used. Only UserPromptSubmit receives `additionalContextLimit`; Stop events cannot return that context. macOS/Linux use shell-quoted executable and script paths. Python must remain at the recorded path; reinstall integration after moving runtimes/skill locations.

Windows integration also creates `<data-dir>/Token Steward Status.cmd` for direct local checks without model calls. It is not an always-running service and does not query live account billing. You can use `status --refresh` directly on other platforms.

## Disable/remove

`remove-integration` removes only marked global instructions and handlers whose status marker is `codex-token-steward`. Other hooks and instructions remain. Analytics are retained. `policy --report-every-message no` suppresses Stop UI messages and makes the installed global command print a disabled notice instead of collecting/printing a footer. Hooks still collect and provide analysis; remove integration to disable those too. A direct `report` request remains available.

To uninstall the skill, remove integration first, then remove only its installed skill directory using normal filesystem tools. Delete the dedicated data directory separately only if the user explicitly wants to erase history. No automatic recursive deletion is shipped.

## Capability boundary

This release provides accounting, diagnostics, compact feedback, project facts, comparison records, model registry maintenance, and local deployment planning. It does not provide a universal hard spending cap, guaranteed cost savings, automatic background billing access, autonomous model switching, remote deployment/database execution, or an always-on daemon. The skill guides authorized execution using available host tools.
