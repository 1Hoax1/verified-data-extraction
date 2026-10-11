# P2 traceability amendment v1.1

| Authority | Requirement | Implementation / evidence |
|---|---|---|
| CR-P3-002 clauses 1–2 | Preserve historical P2 controls and allow only authorized P3 | P2-T40; `tests/scope_policy.py`; frozen P1/P2 inventories and retained negative probes |
| CR-P3-002 clause 3 | Full application audit including new P3 | P3-T51; `tests/p3/scope_allowlist_v1.json`; source/dependency/migration/SQLite/scope negative probes |
| CR-P3-002 clauses 4–5 | Versioned amendment, actual 148-test regression | This supplement; P3 validation report and three JUnit suites |

Original P2 v1.0 design, archive, acceptance criteria and runtime remain unchanged.
