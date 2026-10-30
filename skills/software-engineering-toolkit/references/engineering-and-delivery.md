# Practical implementation, verification, release, and support

## Scope and completion

Define observable acceptance criteria for the next feature without demanding a complete up-front specification. Preserve existing conventions, architecture, working features, and unrelated user changes. Use small coherent changes. Surface consequential new maintenance, hosting, service, or architecture requirements for developer decisions before adopting them.

Before extending an existing project, inspect the affected code paths, interfaces, tests, configuration and documentation. Distinguish observed behavior from intended behavior and ask when they disagree. Restore existing context before making plans. Do not impose a new framework or rewrite because it is familiar.

## Debugging and testing

Reproduce failures under a controlled relevant setup; record symptoms and evidence. Inspect the failing path and likely cause before proposing a patch. Make a focused change, verify the original issue, and check relevant regressions. Preserve unresolved hypotheses and next diagnostic steps in context rather than repeating failed experiments on the next turn.

Select free local tools appropriate to the actual stack. Verify important workflows, permission boundaries, integrations, and failure paths at a useful level. Add meaningful regression tests where practical; do not create tests merely to match implementation wording. State what passed, failed, or could not be tested, with evidence tied to the revision. Completion requires the agreed behavior and necessary checks, not a successful edit or a code review alone.

Build accessible user flows. Evaluate keyboard/focus behavior, readable labels/content, relevant assistive-technology support, validation, loading, empty, error, offline and permission-denied states as applicable. Follow project requirements and relevant current platform guidance; do not claim accessibility conformance solely from an automated scan.

## Shared-host/free-tool execution

The audience commonly has a single server and prefers free tools. At the moment a decision needs it, confirm runtime/version, database, secure upload/deployment mechanism, writable locations, resource limits, scheduling, HTTPS, email, and recovery capabilities relevant to that action. Do not interrogate every capability at kickoff or assume root, SSH, containers, a daemon, Redis, a worker service, or a paid CI account.

Build/test on the developer's machine where appropriate and deploy compatible artifacts. For mobile/games, distinguish local builds/distribution from any hosted backend. Prefer existing tools; discuss new integrations, accounts, costs and material architecture changes. Free tiers can have changing limits, privacy implications and maintenance costs; verify current terms when proposing one. Do not make a project public to obtain free tooling without explicit authorization.

## Release and recovery

Prepare the actual release path when release work is relevant:

1. Identify the exact version/artifact, target, necessary configuration, and acceptance/smoke checks.
2. Verify relevant checks locally or in an existing supported staging environment. Separate staging/test data and credentials from production. Do not invent staging availability or require a second server.
3. Before consequential production/data changes, establish appropriate recoverable backups of files/data/configuration and the recovery procedure available with the developer's access. Protect backups and retain required document history. Use a copy outside the hosting account where approved and available; do not claim a same-account copy covers host loss.
4. Apply necessary versioned migrations with compatibility/recovery planning. Preserve migration execution evidence. Do not assume all database engines or schema operations support transactional rollback.
5. Deploy through the supported secure mechanism, keep sensitive/internal records out of public artifacts, and verify actual deployed behavior and version.
6. If verification fails, follow the authorized recovery plan. Code rollback does not undo destructive migrations or safely discard newly written production data. Explain blockers and obtain consequential recovery decisions rather than retrying destructive actions.

Do not demand a particular branching platform, CI service, blue/green infrastructure, or load balancer. Keep a useful local verification/release path. A manual step can be appropriate if documented and verified. Record actual release and recovery evidence, not a promised outcome.

## Operational visibility and integrations

Start with relevant application error logs, safe diagnostic context, and simple host-supported health indicators/notifications. Protect logs and privileged diagnostic views, avoid secrets and sensitive payloads, and avoid noisy alerts. Add external monitoring only through the developer's integration decision.

For actual external integrations, define appropriate timeouts, bounded retries with backoff where useful, duplicate request/event protection, webhook authenticity, rate-limit behavior, and partial/outage failure handling. Retry only where safe; do not repeat side-effecting operations blindly. Confirm contracts and credentials, record integration dependencies and decisions, and test relevant failure paths without hitting live third-party systems unnecessarily.

## Functioning support and its knowledge

During relevant definition work, clarify who provides/receives support, required channels, issue lifecycle, access/privacy rules, expected workflows, and any escalation needs. Build the agreed support software, not only help pages; do not assume tickets, chat, email, SLAs, or a third-party helpdesk were requested. Keep procedures aligned with the implemented support features.

Maintain relevant troubleshooting, known issues, workarounds, escalation/incident links and user guidance. Connect a support issue to reproducible evidence, business-rule context, a focused fix, verification and knowledgebase/document updates. Protect customer information; use sanitized examples in portable records. Version changed support procedures and business knowledge just like other project documents.

## Reference points

Consult primary sources for the actual stack and current platform limitations. Useful general references, not mandatory services or additional setup requirements:

- [Google SRE release evaluation](https://sre.google/workbook/canarying-releases/).
- [Google SRE monitoring principles](https://sre.google/sre-book/monitoring-distributed-systems/).
- [W3C accessibility evaluation](https://www.w3.org/WAI/test-evaluate/).
- [cPanel cron capability](https://docs.cpanel.net/cpanel/advanced/cron-jobs/) and [backup/restore access](https://docs.cpanel.net/cpanel/files/backup-wizard/), only for projects actually using cPanel.
