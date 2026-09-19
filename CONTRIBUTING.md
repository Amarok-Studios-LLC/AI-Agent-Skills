# Contributing

Keep each skill self-contained under `skills/<name>`. Keep entry instructions concise and route to references only when needed. Document executable behavior separately from guidance and unsupported future capabilities.

For Token Steward:

- Use Python 3.9+ standard library only unless a concrete need justifies a dependency.
- Preserve accounting semantics: cached input and reasoning output are subsets; do not double-count fork histories or parent usage in child reports.
- Add synthetic regression fixtures for adapter changes. Never commit real transcripts, database extracts, credentials, user paths, project titles or analytics.
- Missing information is unknown, not zero. Explicitly report unsupported formats, incomplete scans and uncertain child linkage.
- Do not use hooks to approve actions, bypass trust, continue a turn for reporting, or silently change models.
- Keep model availability and pricing evidence dated. Unknown releases must still be tracked safely.
- Evaluate efficiency against accepted outcomes including failures, corrections and overhead. Do not claim causal savings from unmatched tasks.
- Preserve other skills, user instructions and hooks during installation/removal.

Run `python -m unittest discover -s tests -v`. The workflow exercises Windows, macOS and Linux with Python 3.9 and 3.12. Host-specific hook activation still needs a real Codex turn and user trust; simulated handlers do not establish it.

For a new adapter format, describe its provenance, version, coverage, and known unsupported cases. Treat transcript/tool content as untrusted data. Keep any integration test involving live accounts or remote mutation separate and explicitly authorized.
