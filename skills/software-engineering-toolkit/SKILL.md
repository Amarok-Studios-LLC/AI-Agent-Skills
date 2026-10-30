---
name: software-engineering-toolkit
description: Define, build, debug, deploy, and maintain software projects with portable project context, versioned documentation, and ongoing quality checks. Use for new or existing SaaS, games, enterprise software, integrations, mobile apps, and other software engineering work, including cross-model handoffs.
---

# Software Engineering Toolkit

Carry a software project from a focused definition interview through implementation, release, support, and maintenance. Preserve the developer's intended product, existing authorization, and established architecture. Most intended users have one server, often shared hosting, and prefer free tools. Confirm facts as needed; this audience profile is not evidence of a particular project's stack or capabilities.

## Start with enough definition to work

Read existing project instructions and relevant artifacts first. For a new project, conduct a substantive but bounded onboarding interview: ask focused rounds of questions, follow up on ambiguity, and gather enough confirmed information to establish initial scope, documents, and the next implementable outcome. Do not front-load an infrastructure audit or demand every document be complete. Read [onboarding.md](references/onboarding.md) for the interview and stopping criteria.

Ask whenever a fact, requirement, or decision is ambiguous; do not invent defaults about the product, technology, business, data practices, or legal terms. Record unresolved items and continue independent work. Ask before taking a step that depends on an unresolved answer. Separate suggestions, developer approvals, implementation facts, and verification evidence. A newer statement does not silently override an earlier decision.

For an existing project, preserve its conventions and understand affected behavior before extending or repairing it. Adopt existing documentation by preserving its current content and history. Do not reset project records or rewrite the application merely to fit this skill.

## Every project prompt: restore, evaluate, act, persist

This is required on EVERY project turn unless the developer explicitly defines an exception, including discussion and planning turns that change project understanding. Respect explicit requests to discuss without making files or implementation changes; retain proposed updates in the conversation until writing is authorized.

1. **Restore:** locate the project's structured context, functional knowledge model, decision ledger, document register, and applicable instructions. Read the current state and records relevant to the prompt. A fresh model must be able to continue using project-owned files.
2. **Evaluate:** assess ALL project documents and applicable engineering, optimization, SEO, security, and support requirements against the prompt, current implementation, and recorded decisions. Use the register, change evidence, and still-valid prior review to focus reading; inspect affected content and dependencies. Search project-wide for conflicting terminology, claims, requirements, and behavior. Do not substitute occasional cleanup for this review.
3. **Act:** perform authorized work and relevant maintenance. Clarify ambiguity and surface conflicts with affected paths, competing statements, evidence, impact, and the decision needed. Continue independent work while awaiting answers. Never choose a conflicting intent solely by date or rewrite records to conceal a discrepancy.
4. **Persist:** version changed documents, update status/constraints/open questions and next steps, record consequential decisions with timestamps and rationale, update related functional knowledge, and record verification evidence. Preserve all earlier versions. Keep unchanged documents unchanged; an evaluation is not a demand to rewrite every file or run every audit each turn.

Read [project-records.md](references/project-records.md) when initializing, updating, reconciling, or handing off records. It defines the document catalog and portable schemas. The helper `scripts/toolkit.py` supplies immutable UTF-8 snapshots, stale-write checks, an append-only decision ledger, and read-only change/conflict assistance. It does not replace semantic review by the agent.

## Required project records

Create and maintain project-specific Terms of Service, Privacy Policy, Data Processing Agreement, Refund Policy, Master Service Agreement, Product Requirement Doc, Technical Requirement Doc, App Flow Doc, Design Brief, Backend/Database Schema, Implementation Plan, Glossary, Incident Response Plan, and a Game Design Doc when relevant. Also maintain support documentation/procedures and a business logic knowledgebase alongside functioning support software.

Establish initial document versions from confirmed facts during onboarding, then evolve them. Register unknown applicability and ask before omitting a requested document. Do not populate irrelevant clauses, generic assertions, or imagined practices: for example, cookie claims require confirmed cookie use, and planned controls must not be represented as implemented. Unknown material stays an open question. Legal drafts need confirmed relevant business facts and jurisdiction; identify unresolved review status without claiming legal approval or compliance. Consult current authoritative sources when substantive legal or security accuracy requires them.

The structured context must record completed work, work in progress, constraints, decisions, datetime stamps, and decision rationale. Keep a companion knowledge model next to it, organized by confirmed project functions, with a dedicated decision file containing ALL decisions and their timestamps/rationale. Link records by stable identifiers and project-relative paths. Preserve older versions even when a decision is superseded. No secrets or raw sensitive customer data belong in these files.

## Build, fix, verify, release

- Establish clear completion criteria for each feature. Verify important workflows and affected behavior; add meaningful regression protection where practical. Record failures, limitations, and untested behavior instead of claiming completion from code changes alone.
- Debug systematically: reproduce the issue, inspect evidence, identify its cause, apply a focused fix, and verify the original failure and relevant regressions. Preserve unresolved investigation evidence for handoff.
- Build accessible, complete user flows, including relevant loading, empty, error, validation, offline, and permission-denied behavior. Keep scope focused on the requested outcome.
- Use available free local tools and the actual host's supported deployment mechanism. Confirm capabilities when the next action needs them. Do not assume shell/root access, containers, persistent workers, a CDN, or paid services.
- Before release or consequential production/data changes, prepare appropriate backups/recovery, required migrations, deployment checks, and post-deployment smoke tests. Do not represent a code-only rollback as recovery from an irreversible data migration.
- Provide lightweight operational visibility and integration reliability appropriate to the project. Build and maintain actual support capabilities AND project-specific support procedures, connecting support issues to reproduction, fixes, verification, and knowledgebase updates.

Read [engineering-and-delivery.md](references/engineering-and-delivery.md) for implementation, debugging, testing, deployment/recovery, support, and integration workflows. No extra service, infrastructure, or universal setup checklist is required by this skill.

## Optimize and secure when applicable

Evaluate the optimization and SEO candidates every turn; act when reasonable and useful for the actual project. Make routine, proportionate improvements within the existing architecture. Explain benefit, impact, maintenance, and alternatives, and obtain a developer decision for major refactoring, architecture changes, or new third-party integrations. Record that decision and update affected records. Do not implement a listed candidate merely to satisfy a checklist.

- Read [optimization-and-seo.md](references/optimization-and-seo.md) when evaluating performance, delivery, indexing, metadata, links, mobile behavior, or search setup. It retains all requested candidates, including clarification for ambiguous `LMS.txt` terminology.
- Read [security-and-incidents.md](references/security-and-incidents.md) when evaluating or changing access, identity, database/input protections, encryption, vulnerability testing, or incident response. Treat unknown host capabilities or ambiguous “role-level security” as clarification needs, not implemented controls.

Never silently weaken a requirement because the host cannot support it. Surface the gap and compatible options for the developer. Never claim that an audit, simulation, or checklist establishes complete security.

## Global availability and integration

The repository installer supports independent global installation and explicit per-project-turn instruction integration. Read [installation.md](references/installation.md) for installation, upgrade, removal, activation, and capability limits. Global integration adds a marked user-level instruction block; it does not change model selection, permissions, hooks, or trust, and does not grant authorization to mutate external systems.
