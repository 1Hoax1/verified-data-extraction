# Open Decisions

## Status after final main-chat review

There are no unresolved P1 implementation decisions in the approved v1.0 pack.

The eight decisions from P1 Implementation Pack v0.1 were resolved by the main managing chat as follows:

| ID | Decision | Review result | v0.2 resolution |
|---|---|---|---|
| D1 | Python standard-library SQLite + explicit repositories/UoW, no ORM | APPROVED | Retained unchanged. |
| D2 | WAL + `synchronous=FULL` + foreign keys | APPROVED | Retained unchanged. |
| D3 | Brief/TransformationSpec JSON authoritative in SQLite | APPROVED WITH CORRECTION | Retained; write and trust-boundary rules now require P0 JSON Schema validation, JSON/index consistency and P0 content-hash recomputation. |
| D4 | Workspace-relative paths only | APPROVED | Retained unchanged. |
| D5 | Filesystem-first atomic promotion -> DB commit | APPROVED WITH CORRECTION | Fixed protocol: staging -> durable flush -> atomic no-overwrite promotion -> DB UoW -> metadata + EventLog -> one commit. |
| D6 | Immutable Approval/EventLog DB guards | APPROVED | Retained unchanged. |
| D7 | Partial unique indexes for Approval | APPROVED | Retained unchanged. |
| D8 | Stale `running` ExecutionRun detect-only on restart | APPROVED | Retained unchanged. |

No item above changes Pilot scope, P0 contracts, approval semantics, operation whitelist, order-state model or architecture.

## Change Request

No Change Request is required by this candidate. The review corrections are implementation-level enforcement of already approved P0/Pilot semantics.
