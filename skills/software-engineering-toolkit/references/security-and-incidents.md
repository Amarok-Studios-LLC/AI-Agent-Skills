# Applicable security controls and incident response

Evaluate these policies every project turn against actual features, current changes, known findings, and confirmed constraints. Make proportionate authorized fixes, verify affected boundaries, record unresolved gaps, and clarify uncertain intended behavior. No checklist item should create an irrelevant project feature, service, compliance claim, or infrastructure assumption.

## Requested controls

1. **Protect admin routes:** authenticate and authorize actual privileged entry points, including APIs and alternate paths; exercise denial behavior.
2. **Enforce permissions server-side:** authorize each relevant operation/resource boundary; hiding UI controls is not sufficient.
3. **Role-level security:** clarify role-based access control versus database row-level security when ambiguous. Map confirmed roles/resources/actions and verify applicable isolation. Do not claim row-level controls exist when the engine/host lacks them.
4. **Verify email addresses:** implement the confirmed account flow where relevant, including appropriate verification-token lifecycle and failure behavior. Do not fabricate an email feature for a project that has none.
5. **Hash passwords:** use maintained password-hashing facilities suitable to the actual stack and current authoritative guidance. Never store plaintext credentials in project documentation or invent custom password cryptography.
6. **Parameterized SQL:** use actual driver-supported bound parameters for data, including affected dynamic paths; handle dynamic identifiers through validated allowed structures rather than string-interpolated user data.
7. **Cross-site scripting protections:** apply context-appropriate output handling and safe rendering for actual input/output paths; validate relevant stored and reflected cases. Do not claim a generic filter blocks every injection context.
8. **Encrypt data at rest:** establish relevant data/storage scope, actual provider/application capabilities, and key handling. A host marketing claim is not evidence of complete database/backup/application encryption. Surface unsupported or unverified requirements for a developer decision.
9. **Encrypt data in transit:** verify relevant deployed client/server and integration transports; establish actual termination/configuration boundaries.
10. **Scan for vulnerabilities:** choose appropriate free/local tools for the actual stack/dependencies and authorized target. Verify findings, record affected versions, prioritize actionable issues, and disclose coverage limits.
11. **Simulated penetration testing:** establish authorization, permitted targets, environment, methods, accounts and impact boundaries before execution. Prefer controlled local/test data and nondestructive exercises. Provider/third-party systems are not implicitly in scope. Record evidence and limits; simulation is not certification.
12. **Incident Response Plan:** create a project-specific initial version, then maintain and version it alongside the other project documents.

## Incident Response Plan substance

Gather the actual information needed, when relevant: incident indicators, reporting paths, responsible roles/contacts, severity handling, available logs/evidence, containment capabilities, credential revocation/rotation, restoration, verification of recovery, communication responsibilities, and follow-up work. Do not invent contacts, round-the-clock support, recovery capabilities, legal notification periods, or contracts.

Mark unresolved facts and decisions explicitly. Distinguish a proposed procedure from an exercised one. Legal/regulatory obligations depend on confirmed jurisdiction and circumstances; consult current authoritative sources and clarify applicable requirements before making substantive claims. Keep incident examples sanitized and confidential evidence in appropriate controlled storage.

When incidents or exercises reveal gaps, update the decision ledger, context, procedures, support knowledge and affected implementation/docs, retaining every older document version. A proposed new provider, architecture change or major refactor follows the normal developer-decision rule. Do not silently downgrade a required control to suit the host.

## Evidence and sources

Use actual tests/configuration/evidence and current primary guidance for the project. Relevant starting points include [OWASP ASVS](https://asvs.owasp.org/), [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/), [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/), and [NIST SSDF](https://csrc.nist.gov/projects/ssdf). Select relevant controls; do not require every framework control or an audit before the developer can start building.
