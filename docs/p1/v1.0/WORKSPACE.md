# Local Filesystem Workspace

## Root

The application is configured with one local workspace root. SQLite stores only paths relative to this root.

Recommended P1 layout:

```text
<workspace>/
  app.sqlite3
  orders/
    <order_id>/
      input/
        <asset_id>/
          payload
      runs/
        <run_id>/
          raw/
          intermediate/
          result/
          reports/
          artifacts/
  .staging/
    <storage_operation_id>/
      payload.tmp
  recovery/
    quarantine/
```

Only `input/.../payload` is expected to contain user input bytes during P1. Run directories are structural reservations for later Pilot stages and may remain empty in P1 tests.

## Source of truth

- SQLite is the source of truth for metadata, versions, approvals, run/report/event records and file references.
- Filesystem is the source of truth for file bytes.
- BriefVersion and TransformationSpecVersion are not maintained as parallel authoritative JSON files in the workspace during P1; their authoritative validated contract documents are stored in SQLite.
- Later artifact/export stages may create snapshots without changing this source-of-truth rule.

## Path rules

- Persist only normalized workspace-relative paths.
- Reject absolute paths, drive-qualified paths, NUL characters and any `..` traversal.
- Resolve and verify that the real target remains under the configured workspace root.
- Do not use untrusted original filenames as directory structure.
- Input payload final paths are derived from controlled identifiers (`order_id`, `asset_id`), not user-supplied path strings.
- Symlinks that would escape the workspace root are rejected.

## File write rules

All new durable payloads follow `TRANSACTIONS.md` exactly:

staging -> durable flush -> atomic no-overwrite promotion -> DB UoW -> metadata + EventLog -> one commit.

Additional rules:

- `.staging` must be on the same filesystem/volume as the final destination so promotion does not degrade into copy+delete;
- the staged file is flushed before promotion and size/SHA-256 describe the exact promoted bytes;
- the final destination must not already exist;
- no overwrite-capable fallback is allowed;
- final-directory metadata is synchronized with the strongest supported platform primitive before the DB transaction is committed;
- database metadata is created only after successful promotion;
- if metadata/EventLog insertion or DB commit fails, the DB transaction rolls back and the promoted payload remains an orphan for recovery.

## File deletion

P1 has no user-facing hard-delete workflow. Immutable/versioned artifacts and approvals are not removed. Recovery may quarantine unreferenced incomplete/staging files but does not silently delete committed-looking data or rewrite DB metadata.
