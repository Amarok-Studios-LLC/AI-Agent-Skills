# Choose the appropriate execution path

An AI-generated reply consumes tokens even when the user asks a simple question. A skill is interpreted within an existing model turn; it cannot retroactively make that turn free or transparently reassign it to a different product. ChatGPT conversation uses tokens and may have its own plan limits. Do not promise separate or free billing without verified account-specific evidence.

- General conversation that does not require repository state can be started directly in ChatGPT Chat. Suggest this when useful; do not interrupt each brief exchange with routing advice. The user chooses the destination before sending.
- Keep follow-ups that require task history, code, tools, or verification in the current task when transferring context would create more work or lose information. A short message can still require difficult reasoning.
- Simple conversation here: answer concisely, skip preparation, repository reads, audits, browser research, and delegation unless the question itself requires them. Honor explicitly enabled usage reporting.
- Deterministic checks can run outside the model: `python <skill>/scripts/steward.py status --refresh`, `doctor`, `audit`, or reports for an explicit session. These scripts do not invoke an AI model. Asking Codex to run them still creates a model turn; run them directly for no model-token overhead.
- The Windows integration creates `<data-dir>/Token Steward Status.cmd`. Double-click it for local usage and integration status. It refreshes local records, not live account billing. Reports include their timestamps and missing coverage.

Do not silently switch models, create another chat, forward project history, or automate another product's chat UI as an alleged free backend. A true pre-submission router would require host/client support outside this skill. No such automatic routing is implemented here.

The optional `verify-host` command uses a loopback canned response to exercise hook dispatch with zero model inference. Its generated test response is fixed text, not an AI answer. It preserves the user's persistent model settings, never changes hook trust, and saves no synthetic token usage in session history.

References checked September 2026: [tokens and pricing](https://learn.chatgpt.com/docs/pricing), [skills](https://learn.chatgpt.com/docs/build-skills), [hook lifecycle](https://learn.chatgpt.com/docs/hooks). Recheck current product/account limits before making billing recommendations.
