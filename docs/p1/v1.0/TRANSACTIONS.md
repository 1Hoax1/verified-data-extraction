# Transaction Rules

## SQLite connection policy

For each SQLite connection used by P1:

- foreign keys are enabled;
- WAL journaling is used for the local single-user workspace;
- synchronous durability is `FULL` for write safety;
- a finite busy timeout is configured;
- write transactions are short and explicit.

## Unit of Work

- One Unit of Work owns one SQLite connection/transaction.
- Repository write methods never commit independently.
- A Unit of Work either commits all DB changes or rolls them all back.
- Nested independent commits are forbidden.
- Long-running file parsing, network calls, transformation work or QA computation must never be held inside a DB transaction; these are outside P1 anyway.

## Metadata-only writes

Entity creation/update that does not involve new file bytes is one SQLite transaction. EventLog entries that audit the same mutation are inserted before the same single commit. No audit EventLog append occurs as a second post-commit transaction for that mutation.

## Approval safety support

P1 provides the DB primitives needed for P3 to perform `READY_FOR_APPROVAL -> APPROVED` atomically after checking selected versions, recalculated hashes and exact approvals. P1 does not implement that P3 use case itself.

## File + SQLite write protocol

Filesystem and SQLite cannot share one true ACID transaction. P1 therefore uses one fixed recoverable ordering for every operation that introduces new durable file bytes plus DB metadata:

1. **Staging write** — create a unique controlled path under `.staging` on the same filesystem/volume as the final destination; write bytes only to that staging file.
2. **Durable flush** — flush language/runtime buffers, flush the staged file to the OS/storage using the platform durability primitive, then finalize `size_bytes` and SHA-256 from exactly those bytes. Close/reopen verification may be used by tests; no parsing is performed.
3. **Atomic no-overwrite promotion** — create the final controlled path atomically from the staged payload using a primitive that fails if the final path already exists. An overwrite-capable rename is not an acceptable fallback. After promotion, persist the directory entry with the platform-supported directory-metadata durability barrier where available.
4. **Open DB Unit of Work** — only after the final file exists at its immutable relative path, begin the single SQLite write transaction.
5. **Insert metadata + EventLog** — insert the file-backed metadata row and all EventLog records that belong to the same storage mutation inside that Unit of Work.
6. **Single DB commit** — commit exactly once. Repository methods and EventLog append do not commit independently.

There is no step after the commit that is required to make the metadata/audit mutation durable.

## Collision semantics

- A final path is immutable and must not already exist before promotion.
- Any pre-existing final path causes the storage operation to fail; existing bytes are never replaced, truncated or adopted automatically.
- Matching checksum does not authorize overwrite or auto-adoption.
- A collision with no DB row is treated as a recoverable orphan/collision condition for recovery inspection, not as success.

## Durability semantics

P1's durability guarantee is defined as follows:

- file contents are flushed before final promotion;
- the final directory entry is synchronized using the strongest supported local-filesystem primitive before the DB Unit of Work commits;
- SQLite uses WAL + `synchronous=FULL` for the DB commit;
- if the target platform/filesystem cannot provide the required no-overwrite atomic promotion, implementation must fail the write rather than silently downgrade to overwrite-capable behavior;
- platform-specific limits on directory-entry power-loss durability must be documented and exercised by P1 filesystem/restart tests; P1 does not claim stronger guarantees than the host filesystem exposes.

## Crash/failure consequences

- failure/crash before promotion: only staging material may remain; no DB row exists;
- failure/crash after promotion but before DB commit: an orphan final file may remain; no committed metadata/EventLog exists;
- failure while inserting metadata or EventLog: the DB Unit of Work rolls back entirely; promoted file remains an orphan for recovery;
- successful DB commit: metadata and its audit EventLog are committed together and reference an already promoted file.

Recovery handles staging/orphan files without inventing DB rows. This intentionally prefers a recoverable orphan over a committed DB reference created before its file existed.

## Updates and deletes

- Approval and EventLog are immutable at both repository and DB-guard level.
- BriefVersion and TransformationSpecVersion are append-only through repositories.
- ExecutionRun's identity/reference fields are immutable after creation.
- Artifacts are not overwritten; replacement creates a new Artifact.
- P1 defines no cascade that silently deletes input/artifact files.
