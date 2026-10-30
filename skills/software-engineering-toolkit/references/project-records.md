# Portable context, knowledge, documents, and immutable history

## Project-owned layout

Use established project paths where present. For a new project, the helper supports this portable layout:

```text
.engineering/
  context.json                 Structured working context and document register
  manifest.json                Helper-managed current version metadata
  documents/                   Project-specific documents, normally Markdown
  knowledge/
    decisions.json             All decisions, append-only with explicit supersession
    <confirmed-function>.md    Functional knowledge and business rules
  history/<path-hash>/         Immutable full-content revision snapshots
```

The context and knowledge model live next to each other and travel with the project. Keep these records in the developer's versioned project storage and handoff package, with access appropriate to their contents. Exclude internal records, archives, and configuration from public deployment packages. Never rely on one model's memory or a vendor-specific conversation export to reconstruct the state.

The suggested layout is not a reason to move or delete existing records. Register documents at their existing project-relative paths. Binary artifacts need equivalent immutable copies plus metadata before replacement; the supplied helper handles UTF-8 text only. Git can supplement file snapshots; shallow or missing Git history must not be the only way to recover earlier required document versions.

## Structured context contract

Maintain readable JSON or an equivalent explicitly structured existing format:

- Project identity and confirmed scope; sources for relevant facts.
- `completed`: work identifiers, outcome, completion timestamp, and evidence.
- `in_progress`: work identifiers, current state, owner where known, next action, blockers.
- `constraints`: confirmed restrictions, source, rationale where known, and validity conditions.
- `decisions`: references to stable decision identifiers; include or link timestamp and rationale.
- `updated_at`: an ISO 8601 datetime with UTC or an explicit offset. Preserve supplied original decision dates; do not invent historical timestamps.
- `open_questions`: ambiguity/conflict, affected paths, who can answer, and dependent work.
- `documents`: each requested document's path, applicability/evidence, lifecycle state, revision, dependencies, and open issues.
- `verification`: checks, actual results, timestamp, version tested, and material limits.
- `next_steps`: actionable continuation instructions for a fresh developer/model.

Empty arrays from initialization mean no information recorded, not proof that there are no constraints or open questions. Fill records with confirmed information from onboarding. Keep concise rationale that explains the decision and tradeoffs; do not request or store private model reasoning.

## Required document register

| ID | Document | Project-specific substance to establish |
|---|---|---|
| terms | Terms of Service | Actual service, users, responsibilities, confirmed business/legal facts |
| privacy | Privacy Policy | Actual data, collection, purposes, sharing, storage, retention and user processes |
| dpa | Data Processing Agreement | Confirmed parties, roles, processing relationship and applicable scope |
| refunds | Refund Policy | Actual payment/refund arrangements; clarify relevance before exclusion |
| msa | Master Service Agreement | Actual contracting/service relationship and agreed terms |
| prd | Product Requirement Doc | Problem, users, scope, workflows, acceptance criteria |
| trd | Technical Requirement Doc | Confirmed stack, interfaces, constraints, required qualities |
| flows | App Flow Doc | Actual/intended journeys, permissions, alternate and failure paths |
| design | Design Brief | Confirmed direction, interface expectations and accessibility |
| schema | Backend/Database Schema | Actual or explicitly planned entities, relationships, constraints and migrations |
| plan | Implementation Plan | Sequenced work, dependencies, completion criteria, status |
| glossary | Glossary | Project terms and consistent meanings |
| gdd | Game Design Doc, if relevant | Confirmed mechanics, progression, content and game-specific constraints |
| incidents | Incident Response Plan | Actual contacts/roles, capabilities, response and recovery procedures |
| support | Support documentation and procedures | Actual support software, workflows, troubleshooting and escalation |
| business | Business logic knowledgebase | Rules, calculations, permissions, exceptions and behavior grouped by confirmed function |

The business logic knowledgebase may be the functional portion of the companion knowledge model, with cross-links instead of duplicate conflicting copies. Explain confirmed behavior, reference relevant implementation/tests, distinguish planned from implemented behavior, and document exceptions actually relevant to the project. Preserve requested documents as registered unresolved items if applicability or required facts have not yet been answered.

## Revision protocol

Before changing a current document, preserve its existing version if not already archived. Every substantive revision gets an immutable snapshot with a stable path, increasing version, timestamp, actor, change reason, content hash, and link to its predecessor. Keep a discoverable current version. Never delete, prune, silently replace, or rewrite older required versions. A correction is another revision. Do not fabricate revisions for unchanged content.

The helper archives before replacing current content, checks the expected current hash, and uses a local exclusive writer lock. If a file was edited externally, `track` it before another replacement. If an operation was interrupted, retain the lock/history evidence and inspect; do not automatically remove a lock owned by another writer. The helper is not a distributed transaction manager: coordinate concurrent writers, use version-control merges where appropriate, and reconcile any changed content before retrying. Keep all competing revisions when resolving a conflict.

## Decisions and conflicts

Each consequential decision records `id`, `title`, `decision`, `timestamp`, `actor`, `source`, and `rationale`. Record all developer decisions, including deferrals, rejections, applicability choices, and architecture/integration choices; connect them to affected work/documents. Routine execution detail need not become a new product decision.

Use optional `claims` for precise shared facts, e.g. `{"uses_cookies": false}` after confirmation. Claim keys must have consistent meaning and scope. `supersedes` explicitly names prior decisions that an authorized new decision replaces. Retain original entries unchanged. New timestamps alone never resolve competing values.

On every prompt, search the project's actual documents, code/evidence relevant to claims, and knowledge records for semantic conflicts. Report competing statements, paths/identifiers, evidence, and dependent impact. Correct clear implementation/document drift within authorization; ask when the intended truth is ambiguous. Do not invent a precedence hierarchy that overrides the developer. After resolution, append the decision and version all affected documents/context/knowledge.

`review` reports registered/missing/changed documents, likely untracked Markdown in common documentation locations, merge markers, and contradictions in explicit active decision claims. It does NOT discover every document format/location or interpret prose, code, or legal meaning. Discover/register other project documents with normal file tools and perform the semantic review yourself. An empty helper conflict list is not evidence of global consistency.

## Helper commands

Use Python 3.9+; the helper has no dependencies or network/model calls. Replace `<skill>` with this skill's location. Global options precede subcommands.

```text
python <skill>/scripts/toolkit.py --project <root> init --name <confirmed-name> --actor <actor>
python <skill>/scripts/toolkit.py --project <root> review
python <skill>/scripts/toolkit.py --project <root> track --path docs/product.md --actor <actor> --reason <reason>
python <skill>/scripts/toolkit.py --project <root> publish --path docs/product.md --actor <actor> --reason <reason> --expected <current-sha256>
python <skill>/scripts/toolkit.py --project <root> decide --actor <actor>
python <skill>/scripts/toolkit.py --project <root> review --history
```

`publish` reads the complete new UTF-8 content from standard input. Omit `--expected` only for a new, nonexistent document. `decide` reads a JSON decision object from standard input; it adds a recording timestamp and actor. `track` imports current content without changing it. Use structured tool input or a literal temporary file/subprocess input to avoid shell expansion. Scripts cannot infer whether supplied claims or decisions were authorized; establish evidence and authorization before invoking writes.

For a handoff, include the current context, entire knowledge/decision model, all current documents, preserved history, code revision, actual verification results, unresolved conflicts, and next steps. Verify that project-relative links still resolve after a move.
