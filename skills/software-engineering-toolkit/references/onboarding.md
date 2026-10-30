# Focused onboarding and project definition

## Interview, then begin

Use the developer's existing explanation and project files before asking questions. Ask a focused group of related questions, listen, and drill into answers that affect the next work. Do not use a fixed exhaustive questionnaire. Offer succinct choices when helpful, but never treat a preselected answer or silence as confirmation.

Establish enough of the following to define the initial project truthfully:

- Purpose, intended users, problem, desired first outcome, and what is outside the initial scope.
- Critical user journeys, roles, permissions, business rules, and observable completion criteria.
- Existing code/assets, required platforms, integrations, confirmed stack or constraints, and preferred deployment destination if known.
- Relevant data handled, actual collection/storage/sharing practices, account behavior, and business/payment/refund arrangements. Ask legal identity and jurisdiction questions when needed for substantive legal drafts.
- Visual direction, accessibility needs, relevant game mechanics, and support expectations.
- Known budget and hosting constraints, including the preference for free tools and single-server/shared-host feasibility. Confirm capabilities just before they matter; avoid a host audit at project kickoff.

Do not ask irrelevant categories. For example, a project without payments should not acquire subscription/refund behavior through boilerplate. Unconfirmed applicability remains an open question, rather than an assertion that a feature does or does not exist.

## Bounded stopping condition

End the initial interview once the developer's intended initial outcome, main workflow, important constraints, and next implementation step are sufficiently clear, and ambiguities that would change that step have been resolved. Summarize the confirmed definition for correction. Approval already supplied in the conversation is valid; do not demand repetitive signoffs.

Create honest initial document versions from these answers. Keep unresolved items explicit, with the step they block and who can answer. Initial documents may be brief, clearly marked drafts; finishing every legal/commercial detail is not a prerequisite to independent implementation. Continue asking when later work actually depends on an unresolved answer. Do not guess just to finish onboarding.

## Terms requiring clarification when encountered

- **Knowledge organized by function:** confirm whether the developer means product/business capabilities, code-level functions/modules, or another organization. Propose a useful structure, but do not adopt it as a confirmed requirement without an answer. Preserve an existing confirmed organization.
- **Role-level security:** clarify intended role-based permissions versus database row-level security where the distinction affects implementation. Enforce confirmed access rules server-side; do not invent database support.
- **LMS.txt:** ask whether `llms.txt` or a different project-specific file is intended. Do not silently rename the requirement or claim a particular file guarantees search rankings or AI discovery.

These are configurable project questions, not mandatory blockers at the start of every project. Resolve each before the work that depends on its answer.

## Onboarding output

Initialize portable context and knowledge/decision records after the project identity is confirmed. Register the requested documents, their current paths, applicability (confirmed applicable, confirmed inapplicable, or unresolved), lifecycle state (draft, approved, implemented, verified, superseded), sources, open questions, and relevant dependencies. Ask before excluding a requested document. The Game Design Doc is conditional on game relevance.

Record initial scope and consequential developer decisions with timestamps and concise rationale. Follow the portable record protocol; never use chat history as the only copy of an answer needed for the project.
