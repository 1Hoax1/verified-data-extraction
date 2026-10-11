# P3 implementation traceability

Authority: approved P3 Pack v1.0, implementation start on `ba73d05`, CR-P3-002. Original design sources remain unchanged.

| Pack trace / AC | Implemented boundary | Actual acceptance IDs |
|---|---|---|
| TR001 / AC01 | Existing P1 Orders/InputAssets, explicit P2 verification | P3-T01–T03, T31 |
| TR002 / AC02 | Full P0 JSON validation, immutable append/index/hash | T05–T07, T10, T38 |
| TR003 / AC03 | Output-name default/trim/NFC, closed nested criteria | T08–T09, T48 |
| TR004 / AC04 | Internal local-user Brief Approval, exact target, null context | T12–T15 |
| TR005 / AC05 | Approved Brief context, closed 12-operation schemas | T16–T17, T20–T24 |
| TR006 / AC06 | Ephemeral chosen options persisted exactly in Spec | T03, T18–T20, T47 |
| TR007 / AC07 | Separate Spec Approval + atomic APPROVED/COMPLETE | T26–T29 |
| TR008 / AC08 | Missing/mismatched facts block before handoff source I/O | T13, T21, T27, T30–T31, T33, T38 |
| TR009 / AC09 | Immutable revisions and historical approvals, pre-final only | T25, T32, T43–T45 |
| TR010 / AC10 | P0 legal transitions, no APPROVED reopening | T04, T11, T34, T43 |
| TR011 / AC11 | P1 UoW, full CAS, EventLog, one commit and rollback | T10, T24, T29, T35–T36, T49 |
| TR012 / AC12 | Session JSON editor, persisted review/diff, two confirms | T39–T40, T42 |
| TR013 / AC13 | Fresh-process verified reads; no inferred Approval flag | T37–T38 |
| TR014 / AC14 | Ready-only mutations; explicit degraded verified reads | T41 |
| TR015 / AC15 | Read-only handoff, complete scope and regressions | T30, T40, T46–T52 |

Runtime modules: `src/vde/workflow/service.py`, `validation.py`, `errors.py`, `read_model.py`, `ui.py`; authorized integration `src/vde/app.py`. P3 transaction source checks reuse P1 Workspace verification and P2 reader APIs under the already-owned UoW, avoiding nested BEGIN IMMEDIATE. No P1/P2 runtime adapter or contract was modified.

Every P3-F01–F40 setup profile is instantiated through its declared setup actions and verified before scenario actions. F09 uses P0 Schema; F10/F20/F21/F38 use P1 defensive guards; workflow Approvals accept no Approval JSON. Runtime outcomes are in `scenario-results.json`; verifier output is independent design evidence. Acceptance ID results and durations are in `TEST_STATUS.md`.

CR-P3-002: P2-T40 keeps all original negatives and frozen P1/P2 coverage; P3-T51 owns new whole-app inventory, reviewed surfaces/hashes, dependencies, migrations and forbidden scope probes. Historical P1-T30 remains unchanged. Original P2 Pack is unchanged; versioned amendment lives in `docs/p2/amendments/v1.1/`.
