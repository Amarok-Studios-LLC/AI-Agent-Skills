# Global installation and portable operation

## Repository installer

From a checkout of `Amarok-Studios-LLC/AI-Agent-Skills`:

```text
python install.py --skill software-engineering-toolkit
python install.py --skill software-engineering-toolkit --integrate
```

The first command installs the self-contained skill in `$CODEX_HOME/skills/software-engineering-toolkit`, or `~/.codex/skills/software-engineering-toolkit`. The second also explicitly merges the toolkit's marked instructions into user-level `$CODEX_HOME/AGENTS.md`. Use `--codex-home <path>` for a selected installation and `--upgrade` only after reviewing replacement of an identified existing copy. Existing identical files are accepted. Review local customizations before upgrading; the installer does not erase extra unrelated files.

Plain skill installation makes the skill globally discoverable, with implicit invocation allowed. The global instruction integration supplies the requested every-project-turn behavior across future project chats. It preserves other user instructions and saves the previous global instruction file before changes. It does not install hooks, change hook trust, set a model, bypass permissions, create project records in unrelated chats, or start a daemon.

Start a new chat or reload instructions to pick up installed skill/global-instruction changes. Do not interrupt a developer's active work merely to reload. Installation is local to this Codex home; other machines/accounts need their own installation. Project context and knowledge remain portable files that other models/developers can read without this Python helper.

## Disable/remove integration

```text
python <installed-skill>/scripts/toolkit.py remove-integration
```

For a custom Codex home, pass `--codex-home <path>` before the subcommand. Removal deletes only the marked toolkit instruction block and retains integration backups, the installed skill, and all project records/history. Other instructions, hooks, configuration, and Token Steward remain intact. Remove the installed skill folder separately only when explicitly requested; never recursively erase project history as part of uninstalling a skill.

## Guarantees and limits

The instructions define an agent workflow, not a hard enforcement or background monitoring service. They cannot make an inactive model maintain a project between prompts, make another model automatically read files, grant deployment permissions, establish legal approval, or prove complete security. A cooperating model must load the instructions/records and perform the review.

The Python helper implements immutable UTF-8 revision snapshots, expected-hash updates, basic local writer exclusion, decision recording/supersession, and read-only change/explicit-claim conflict reporting. It does not perform semantic conflict resolution, full document discovery, code optimization, deployments, security scans, penetration tests, support hosting, legal drafting, or billing. Those are agent-guided tasks using available authorized tools. No API key, third-party Python package, paid service or network is required by the helper.
