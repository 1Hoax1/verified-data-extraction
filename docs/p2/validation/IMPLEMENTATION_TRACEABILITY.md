# P2 implementation traceability

Authority: approved P2 Implementation Pack v1.0 (unchanged ZIP), frozen P0/P1, and [CR-P2-001](../../change_requests/CR-P2-001.md). `Tnn` denotes P2-Tnn. Runtime results and checked SHA are in [P2_VALIDATION_REPORT.md](P2_VALIDATION_REPORT.md); this mapping alone is not validation.

| Pack trace ID | Implemented boundary | Acceptance tests |
|---|---|---|
| P2-TR-001 | `local.py` extension/ownership, `ui.py` one existing Order/input, `xlsx_reader.py` explicit sheet | T01/T23/T31/T32/T40 |
| P2-TR-002 | `csv_reader.py` explicit codec/delimiter/logical header, strict decode/parse | T03..T11/T22 |
| P2-TR-003 | `preview.py` exact P-A shape, retained first five | T03/T18/T20 |
| P2-TR-004 | selected-only read-only openpyxl adapter, P-B cached scalar equality | T23..T26/T28/T32 |
| P2-TR-005 | full selected OOXML cache element/type scan; late cache failure | T27/T43 |
| P2-TR-006 | one full warning + separate golden summary, bounded samples | T26/T42/T50 |
| P2-TR-007 | `local.py` exclusively delegates registration/read to P1 Storage | T02/T33..T36/T38 |
| P2-TR-008 | `diagnostics.py` validates unchanged execution_error schema; storage faults propagate | T10..T17/T24/T27/T29..T31/T37/T38 |
| P2-TR-009 | fail closed to exception with no result; corrupt deflate/XML/unsafe declarations/paths | T11..T17/T19/T29/T41 |
| P2-TR-010 | unchanged UoW/Storage and migration/runtime SHA audit | T01/T02/T34/T38..T40/T51 |
| P2-TR-011 | static whole-application inventory/import/call/definition/dependency and changed-path policy, negative probes | T20/T21/T36/T40 |
| P2-TR-012 | direct reads of immutable P0 goldens; approved archive/manifest checks | T03/T25..T27/T39/T54 |
| P2-TR-013 | P1 fixture prepares Order; no production seed/create UI; actions alone register/preview | T01/T35/T40 |
| P2-TR-014 | all 21 approved XLSX and 12 CSV reader cases + byte/hash verification | T27..T30/T37/T41..T50/T52..T54 |
| P2-TR-015 | physical XLSX row 1 enforced; no auto-seeking header | T23/T24/T41 |
| P2-TR-016 | `<v>` presence checked independently of openpyxl None; empty string projection | T27/T42/T43 |
| P2-TR-017 | finite scalars, bool/null/date/datetime/time/error projection; leap-day rejection | T25/T49/T50 |
| P2-TR-018 | EOF scan, counters, header + five rows, no dataset handle; checkpoint + independent RSS | T18/T19/T30/T52..T54 |
| P2-TR-019 | ZIP-global preflight before inflation; actual inflated byte counts before ZipExtFile truncation | T29/T30/T44..T47/T52/T53 |
| P2-TR-020 | header-only success is preview, has no QA verdict | T16/T48 |
| P2-TR-021 | degraded writes refused; opt-in verified read; blocked operations refused; no repair | T34/T38/T51 |
| P2-TR-022 | CR phase boundary, original normative packs unchanged, explicit policy amendment | T39/T40/T54 |

P1-T30 retained with the explicit P1 inventory in `tests/scope_policy.py`; all original negative imports/names/table checks remain. [Versioned P1 test-plan amendment](../../p1/amendments/v1.1/P1_TEST_PLAN_AMENDMENT.md) and [traceability amendment](../../p1/amendments/v1.1/TRACEABILITY_AMENDMENT.md) record the authorized interpretation. P2-T40 checks the full application including `app.py`; changing the historical P1 boundary grants no new product behavior.

No P0/P1 normative artifact, P1 production storage/model/repository/recovery contract or approved P2 archive is changed. No new database table/migration, Order workflow, approval UI, transformation, QA computation, export, LLM or network ingestion is implemented. Gate B and P2 VALIDATED still require a separate owner decision.
