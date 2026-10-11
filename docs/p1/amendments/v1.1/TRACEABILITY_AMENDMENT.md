# P1 Traceability Amendment v1.1

Authority: [CR-P2-001](../../../change_requests/CR-P2-001.md) and [test-plan amendment](P1_TEST_PLAN_AMENDMENT.md). Original [v1.0 traceability](../../v1.0/TRACEABILITY_MATRIX.md) is immutable.

| Original requirement | Application during P2 | Executable evidence |
|---|---|---|
| P1-TR-001 / single local app | Historical P1 inventory plus whole-application boundary | P1-T30, P2-T40 |
| P1-TR-002 / persistence workspace only in P1 | Explicit validated P1 module allowlist, frozen runtime bytes | P1-T01..T42, P2-T40 |
| P1-TR-003 / datasets remain files | Original exact table-set assertion retained, no new migration/row table | P1-T30, P2-T40 |
| P1-TR-012 / no QA engine in P1 | P1-only forbidden names retained; P2 whole-tree blocks QA computation/authorship | P1-T27/T30, P2-T36/T40 |
| P1-TR-020 / no service or worker | P1 prohibitions retained; whole-tree new import/call/definition and dependency audit | P1-T30, P2-T40 negative probes |
| P1-TR-021 / no ingestion in P1 | P1 modules still prohibit csv/openpyxl; only P2 readers/UI permitted outside them | P1-T30, P2-T40 |
| P1-TR-022 / Pilot exclusions | Full application inventory and import/call/definition/dependency review | P1-T30, P2-T40 negative probes |
| P1 persistence/approval/version/recovery invariants | No runtime changes; historical assertions unchanged | All P1-T01..T42, P2-T02/T33..T38/T51 |

Actual run results, tested SHA and constraints: [P2 validation evidence](../../../p2/validation/P2_VALIDATION_REPORT.md). The CR changes only the audit's phase boundary; it waives no test or runtime acceptance criterion.
