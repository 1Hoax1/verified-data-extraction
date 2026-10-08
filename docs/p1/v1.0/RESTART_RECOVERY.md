# Restart and Recovery Behavior

## Objective

After process restart, durable metadata and workspace bytes must still be available and internally consistent. P1 recovery detects/contains storage-level interrupted writes where safe; it does not resume business execution, invent state transitions, rewrite authoritative contract JSON or create approvals/runs/reports.

## Startup recovery sequence

1. Resolve workspace root and database file.
2. Verify database can be opened.
3. Verify migration history and migration checksums.
4. Run SQLite integrity/foreign-key checks.
5. Verify required workspace directories and writeability.
6. Reconcile `.staging` entries.
7. Check DB-referenced InputAsset/Artifact paths for confinement, existence and checksum when recovery policy requests the full scan.
8. Detect unreferenced final payloads under controlled workspace locations.
9. Verify persisted contract trust-boundary invariants for BriefVersion, TransformationSpecVersion and QAReport in the configured recovery scan.
10. Detect `ExecutionRun.status=running` records left by a prior process.
11. Return a RecoveryReport/health result to bootstrap.

## Recovery rules

### Incomplete staging file

A staging file is never considered committed data. Retain/move it under recovery quarantine according to policy; do not create a DB record from it automatically.

### Orphan final file

If a controlled final payload exists but no DB record references it, do not auto-import or overwrite anything. Report/quarantine it as orphaned so SQLite remains the metadata source of truth.

### Missing referenced file

Do not delete or rewrite the DB row. Emit a P0-valid `STORAGE_ERROR`; the affected object is unusable until manually repaired/recreated by the appropriate later-stage workflow.

### Checksum mismatch

Do not update the stored checksum to match altered bytes. Emit a P0-valid `STORAGE_ERROR` and block use of that object.

### Corrupt BriefVersion/TransformationSpecVersion

Recovery/trust-boundary verification repeats the critical P0 checks:

- JSON parses and validates against the exact entity schema;
- indexed identity fields match JSON identity fields;
- content hash recomputes exactly from the approved P0 semantic payload rules;
- TransformationSpec's Brief id/hash resolves exactly.

Any mismatch is storage corruption. Do not normalize, mutate, rehash or create a replacement version automatically. Any Approval whose target hash no longer matches is not valid for use.

### Corrupt QAReport/index mismatch

Recovery verifies P0 QAReport schema validity, indexed-field equality with `report_json`, and exact run/version tuple equality. Do not rewrite indexed fields from JSON or rewrite JSON from indexed fields automatically.

### Exact-reference corruption

Foreign-key/integrity-guard violations, missing target versions, cross-order references or Approval/run mismatches block use of the affected record and are reported through the P0 storage-error contract. Recovery does not invent replacement references.

### Running ExecutionRun after restart

P1 never auto-resumes, auto-fails or auto-cancels the run. Recovery reports it as stale/incomplete and leaves the persisted business state unchanged. A later explicitly approved execution/recovery use case may decide the state transition.

### Database integrity failure

Block write-capable startup. Do not recreate the database automatically from files because filesystem contents are not a complete source of truth for metadata, approvals, versions and events.

## Restart guarantee tested in P1

At minimum, a process-close/reopen cycle preserves and correctly reloads:

- Order and status;
- InputAsset metadata and bytes;
- BriefVersion and verified JSON/index/hash invariants;
- TransformationSpecVersion and exact Brief link;
- Approval and exact target/context relationship;
- ExecutionRun and exact version/Approval relationship;
- Artifact metadata and bytes;
- QAReport and JSON/index/run consistency;
- EventLog and same-order run relationship.

This is persistence verification, not execution of P2-P5 workflows.
