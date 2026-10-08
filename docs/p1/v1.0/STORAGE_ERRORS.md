# Storage Errors

## Normative public error contract

P1 does not define a new public storage-error schema. Every persistence/workspace error exposed through the shared structured error channel must validate against the unchanged P0 `execution_error.schema.json` and approved registries.

For P1 storage failures:

- public `code` is exactly `STORAGE_ERROR`;
- public `category` is exactly `STORAGE`;
- severity, stage and every other public field/value must come only from what the validated P0 contract permits;
- P1 must not add a new top-level error code, top-level field, enum value or stage value;
- P1 must not loosen `additionalProperties=false` or otherwise bypass P0 schema validation.

If the P0 schema requires a `stage`, implementation selects only an already permitted P0 value appropriate to the calling boundary. This pack intentionally does not invent a P1-specific stage vocabulary.

## Internal diagnostics are not part of the P0 contract

Implementation may use typed internal exceptions/reasons such as database-open failure, migration drift, constraint violation, record corruption, path escape, missing file, checksum mismatch, atomic-write failure, final-path collision or orphan-file detection.

These internal reasons:

- are not new P0 error codes;
- are not new public top-level fields;
- must not be serialized as `storage_reason` or another extra field unless the exact validated P0 schema explicitly permits that location/value;
- may appear in developer logs or internal exception types;
- must be mapped to a P0-valid `STORAGE_ERROR` object before crossing the public/domain boundary.

## Mapping rules

- migration/integrity failures are startup-blocking;
- path escape is blocking until path/configuration is corrected;
- missing file/checksum mismatch makes the affected stored object unusable and is never silently repaired by changing metadata;
- final-path collision never overwrites the existing file;
- repository/DB constraint failures roll back the Unit of Work;
- stack traces remain in developer logs only, never in the user-facing P0 error object;
- if SQLite itself is unavailable/corrupt, error reporting must not depend on successfully writing that same database.

## Validation requirement

P1 tests must validate representative storage failures against the exact P0 execution-error JSON Schema and registries. A storage error that requires a non-P0 code/field/stage is a design failure, not a reason to extend the contract inside P1.
