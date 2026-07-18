# Pilot Error Policies

| Situation | Policy | Result |
|---|---|---|
| Invalid Brief/Spec/criterion | Confirmation blocked | READY_FOR_APPROVAL |
| Missing/mismatched approval or hash | Execute blocked before input I/O | READY_FOR_APPROVAL |
| Missing/unreadable/unsupported input | Fail fast; no partial dataset | FAILED |
| Unknown operation/property/enum | Schema error; approve/execute forbidden | READY_FOR_APPROVAL or FAILED if stored contract is corrupt |
| Missing column | Fail, except drop_columns.ignore_missing=true | FAILED |
| Rename/output collision | Fail; no auto rename | FAILED |
| parse errors=FAIL | First error stops pipeline and records row/value | FAILED |
| parse errors=SET_NULL | Value becomes null; audited | QA decides |
| drop_missing/deduplicate | Only explicit approved deletion; audit rows/counts | Continue |
| Export or round-trip mismatch | Preserve previous artifact; new result not ready | FAILED |
| Deterministic BLOCKER/ERROR fail | Cannot be overridden | NEEDS_FIX |
| Permitted warnings only | Show explicitly | READY allowed |
| Storage failure | No silent continuation | FAILED |

There are no URL, HTTP, JSON, pagination or LLM policies in Pilot.
