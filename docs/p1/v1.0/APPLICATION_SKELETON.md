# Application Skeleton

## Architectural shape

P1 keeps the approved single-process architecture. The skeleton has no internal network boundary and no worker process.

Recommended package responsibilities:

- `app` — process bootstrap and minimal Streamlit entry point; no Pilot workflow yet.
- `config` — local configuration, workspace root and database path.
- `domain` — persistence-facing entities/enums for the approved model; no P2/P3/P4 services.
- `contracts` — read-only access to the validated P0 schemas, registries, approval rules and content-hash specification. P1 must vendor or reference the validated P0 artifacts unchanged when implementation begins.
- `persistence` — SQLite connection policy, migrations, mappers, exact-reference guards, repositories and Unit of Work.
- `storage` — workspace path policy, staging/promotion, checksums, durability barriers, integrity checks, recovery scan and P0-compatible storage-error mapping.
- `tests/p1` — P1-only unit/integration/restart tests.

Modules for ingestion, transformation, QA computation, LLM, Telegram, marketplace integration or network services are not created in P1.

## Dependency direction

`app -> domain/contracts -> persistence/storage`

Persistence and storage may depend on domain identifiers/value objects and validated P0 contracts, but domain code must not import SQLite or filesystem implementation details.

## Trust boundaries

P1 treats the following as integrity trust boundaries:

- appending a BriefVersion or TransformationSpecVersion;
- appending an Approval;
- appending an ExecutionRun;
- appending a QAReport;
- loading a version/report for later approval, execution or QA use;
- restart/recovery integrity verification.

At these boundaries, repositories must invoke the validated P0 contract/hash checks defined in `PERSISTENCE_MODELS.md` and exact-reference checks defined in `SQLITE_SCHEMA.md`/`REPOSITORIES.md`. P1 does not redefine those rules.

## Bootstrap sequence

1. Resolve local configuration and workspace root.
2. Ensure required workspace directories exist.
3. Open SQLite using the P1 connection policy.
4. Check/apply pending P1 migrations.
5. Run database integrity/foreign-key checks.
6. Run workspace and persisted-contract recovery/reconciliation checks.
7. Expose a ready/degraded/blocked bootstrap result to the Streamlit shell.

Bootstrap performs no ingestion, execution, QA computation or automatic business-state transition.
