# P1 Test Plan Amendment v1.1 — regression boundary during P2

Authority: [CR-P2-001](../../../change_requests/CR-P2-001.md), APPROVED, decision revision `CR_P2_001_APPROVED_2026-10-11`. Applies only to P1 regression during approved P2 implementation. Original [P1 Pack v1.0](../../v1.0/P1_TEST_PLAN.md) remains byte-identical and historically authoritative. No P0 schema, P1 runtime contract, persisted schema, approval/hash rule or recovery behavior changes.

## P1-T30 interpretation

Retain P1-T30 and its negative assertions. Audit the following explicit P1-owned Python inventory from validated commit `1a51c3605fc69c758d9cabd0eab0246c4c386870`:

- `src/vde/__init__.py`
- `src/vde/bootstrap.py`
- `src/vde/config.py`
- `src/vde/contracts.py`
- `src/vde/errors.py`
- `src/vde/models.py`
- `src/vde/recovery.py`
- `src/vde/storage.py`
- `src/vde/workspace.py`
- `src/vde/persistence/__init__.py`
- `src/vde/persistence/database.py`
- `src/vde/persistence/repositories.py`
- `src/vde/persistence/uow.py`

Executable boundary: `tests/scope_policy.py::P1_MODULES`. Every path must exist. Retain the exact original forbidden imports (`sqlalchemy`, `httpx`, `requests`, `urllib3`, `openai`, `telegram`, `fastapi`, `celery`, `rq`, `pandas`, `openpyxl`, `csv`), forbidden workflow/module names and exact SQLite table-set assertion. All other P1 tests remain unchanged, including persistence, immutable Approval/EventLog, version/schema/hash references and recovery invariants.

`src/vde/app.py` is the approved P2 UI integration entry point; it is outside the historical P1-only import audit and **inside** P2-T40. `src/vde/ingestion/` is similarly audited by P2-T40. No skip/xfail, removed test, bypass monkeypatch or general exemption is introduced. No P1 production file is changed.

## Required P2 whole-application audit

P2-T40 audits the entire application inventory, including `app.py` and every P2 module. The versioned policy `tests/p2/scope_allowlist_v1.json` enumerates all approved source paths, Python import/call/definition surfaces and frozen P1 source/migration SHA-256 values. New or removed surfaces require explicit review of a policy diff; the test never regenerates its allowlist automatically.

The audit rejects additional application packages/modules/data files/migrations, changed P1 runtime/migration bytes, new imports, new workflow/creation/export/network/arbitrary-code calls or definitions, unapproved direct/optional/build dependencies, changed existing transitive dependency graphs/sources/versions and unauthorized entry points. Only pinned openpyxl 3.1.5 with et-xmlfile 2.0.0 is added to the validated dependency baseline. Generated `__pycache__` and editable-install `.egg-info` are excluded from application inventory.

Negative copies of the application exercise prohibited HTTP/URL/socket integrations, ORM, LLM, Telegram, browser automation, queues/workers/services, DataFrame imports, dynamic import/exec/eval/subprocess, JSON ingestion, Order creation, P3 approvals/specs, execution/QA/export, added modules/migrations/tables and altered dependencies/lock versions. Existing P1 tables for future workflow remain permitted; P2 never authors those workflow records. Static audit supplements source review; it is not a proof against intentionally obfuscated semantics within an already allowed call.

## Verification and release

P1-T01..P1-T42 must execute and PASS; P2-T01..P2-T54 must execute and PASS, including P2-T40 negative probes and P2-T54 fixture/RSS validation. Actual results belong in the [P2 Validation Report](../../../p2/validation/P2_VALIDATION_REPORT.md), with tested commit and JUnit evidence. This amendment does not close Gate B, authorize merge, declare P2 VALIDATED or authorize P3.
