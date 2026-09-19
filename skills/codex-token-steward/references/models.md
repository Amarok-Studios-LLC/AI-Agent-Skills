# Models that change over time

`steward.py models` lists known role hints, observed unknown models and IDs from the local host model cache when present. The cache is advisory; a listed model may not currently be available. Unknown models still receive token accounting and never inherit a guessed price/capability from their name.

Use the host's model-selection capabilities and current official documentation to verify model IDs, reasoning levels, modalities, context limits, client/account access, service tiers and prices. Refresh when a new model is observed, a routing decision needs current information, or evidence is stale. Don't browse every message. Don't treat an API model list as proof of ChatGPT-plan access.

Official references:
- https://learn.chatgpt.com/docs/models
- https://learn.chatgpt.com/docs/pricing
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://developers.openai.com/api/docs/pricing

Keep user choices fixed unless changes are authorized. A skill cannot universally switch the running model. Configure supported subagent models or recommend a user change only where appropriate. No self-modifying global defaults. Preserve a capable lead for difficult interpretation; route bounded work only when briefing, handoff, verification, cache effects and rework justify it.

## Importing verified rates

`models --import-file <local-registry.json>` merges model entries and append-only rate versions. Existing rate versions cannot silently change. Separate billing contexts by `unit` (`USD` or `credits`) and exact `service_tier`. Never infer a missing service tier as default.

Required rate fields: `model`, `service_tier`, `unit`, `input`, `cached`, `output` (per million tokens), `effective_from`, `checked_at` (YYYY-MM-DD), `source` (official HTTPS URL). Optional `effective_until` is exclusive. Do not backdate a rate unless the source supports that historical applicability. Imported data is user-maintained; URL validation does not verify the factual price. No automatic pricing scrape or network call occurs.

The bundled `models.json` provides discovery hints, not benchmarks or routing mandates. New models begin unvalidated for this user's workload. Compare explicit outcomes and rework before making a persistent recommendation. Expired or unknown price coverage is reported, not filled with a guess.
