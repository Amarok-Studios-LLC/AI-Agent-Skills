# Remote operations: minimize unnecessary work, preserve recovery

This skill plans and supervises efficient operations using the environment's authorized tools. It does not ship an FTP client, database driver, credential store, automatic uploader, or arbitrary SQL executor. The local manifest helper is functional; remote execution remains with existing deployment/database tools and project procedures.

## Environment profile

Record target identity (staging/production), protocol, permitted operations, remote root, artifact layout, persistent paths, deployed revision/manifest provenance, database migration state, verification and recovery method. Store credential references, never credentials. Validate targets before mutation. Reuse session connections and inventories where tools support it and state remains valid.

FTP, FTPS and SFTP have different capabilities. Detect supported rename/staging/hash/resume behavior; never assume remote atomic switching or checksums exist. Use appropriate existing transport security; don't introduce plaintext credentials to optimize convenience.

## Deploy only the intended delta

1. Establish actual deployed state. A local Git diff does not prove the remote state matches a commit.
2. Build a manifest from the deployable artifact, including generated assets and explicit project exclusions.
3. Compare to a verified prior artifact/remote manifest; invalidate it on out-of-band remote changes.
4. Review changed paths, deletion candidates, persistent data and recovery coverage.
5. Use an authorized deterministic transfer script with bounded retries and checkpoints; avoid one model invocation per file.
6. Reconcile uncertain transfers after disconnects. Verify files and application behavior at the destination.
7. Record the resulting manifest/revision and verification evidence for the next deployment.

Helpers (write manifests outside deployable artifacts):

```text
steward.py manifest --root <build-directory> --output <local-manifest.json> --exclude "uploads/**"
steward.py plan-deploy --before <verified-prior.json> --after <local-manifest.json> --remote-verified
```

`--remote-verified` records the user's assertion; it does not perform a remote check. Plans never upload or delete. `.git`, local agent metadata, `.env*`, common dependency/cache directories are excluded by default. Inspect project-specific runtime needs: a directory named `node_modules` may be needed for a nonbundled runtime; use a deliberately prepared artifact/other tooling rather than assuming the default manifest fits all projects. Hidden secrets outside known patterns are not automatically detected. No manifest is itself a backup.

## Backups based on recovery coverage

Ask what unique state would be lost and how it would be restored. If committed source plus retained/locked build inputs genuinely reproduce the deployed artifact, an extra source archive may add no protection. Verify that recovery remains accessible. Git does not protect database contents, uploads, untracked files, server-only settings, or unknown remote edits. Back up affected unique state where needed; reuse verified recovery protection when still valid. Do not override an explicit backup requirement silently. Identify the instruction source and propose a narrow correction if redundant.

## MySQL

Use existing authorized connections/tools. Discover server/version/storage engine and schema/migration state as needed; don't repeatedly enumerate everything. Cache a bounded schema summary with validity conditions. Prefer targeted queries, server-side aggregation, parameterized inputs and bounded result sizes. Large read queries can still create load; inspect execution plans for expensive work when appropriate.

For mutations, confirm affected data and target, migration identity/idempotency, transaction and locking behavior, recovery and verification. Prefer set-based changes or controlled batches when valid. A disconnected write may already have committed: reconcile migration state/data before retrying. Don't assume DDL or every storage engine participates in rollback. Versioned migrations are not a backup of production data. Avoid blind full database dumps or blind omission of recovery measures.

Record affected rows, query/transfer duration, bytes, retries, failed checks and rework only when tools actually expose them. Token volume is a separate measurement. Small transfers do not automatically save model tokens; removing unnecessary agent/tool round trips often does.
