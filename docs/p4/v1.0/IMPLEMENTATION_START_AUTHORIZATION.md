# P4 — Implementation Start Gate authorization

**Owner decision:** APPROVED / OPEN, 2026-10-30.  
**Decision revision:** `P4_IMPLEMENTATION_START_AUTHORIZED_2026-10-30`.  
**P4 stage:** IN_IMPLEMENTATION — implementation work authorized; no P4 runtime or test evidence is asserted by this approval.  
**P4 Gate A:** CLOSED / PASS, approved pack v1.0.  
**P4 Gate B:** NOT_RUN / NOT_PASSED.  
**Scope:** Pilot Slice V1 P4 only, strictly as specified in the approved ZIP and binding CR-P4-001.

## Authority and immutable baseline

- Exact owner confirmation: main managing chat, after the GitHub upload of the approved archive was independently verified.
- GitHub `main` at authorization: `8ae219d717b36f463ea76eccaeb8c88d74aeeefc`.
- Source-of-truth approved pack: `docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip`; SHA-256 `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa`, 112649 bytes.
- Governing decisions: P4-Q01..Q05 and Q07 APPROVED; P4-Q06 DEFERRED; P4-D01..D14 approved only where consistent with higher-authority contracts; D15 DEFERRED. CR-P4-001 APPROVED / NOT_IMPLEMENTED until implemented and validated.
- No P0/P1/P2/P3 changes are implied by implementation start. P0 contract pack remains authoritative and its 13 missing P-C files in GitHub are a known separate integrity discrepancy.

## What may be implemented

1. `src/vde/execution/` P4-only modules according to `MODULES_AND_API.md`, `ENGINE_AND_OPERATION_SEMANTICS.md`, `WORKFLOW_AND_TRANSITIONS.md`, `ERROR_POLICIES.md` and `PERSISTENCE_AND_PROVENANCE.md`.
2. Fresh P1/P3 preflight and exact double-Approval/version/hash/order verification **before source file I/O**, using the current P3 `P4Handoff` and the P1 UnitOfWork/CAS contract.
3. Full-row verified single-dataset local CSV or selected XLSX worksheet reader without changing P1/P2 production code or treating P2's five-row preview as full data.
4. Deterministic sequence of the **12 already approved P0 operations only**, exact semantics and first-error policies, immutable InputAsset, auditable counts and source selection.
5. P1-native durable `ExecutionRun` + internal `Artifact` with P4 `succeeded` meaning committed internal transform, *not* P5 QA or Order READY; P4→P5 `P4_INTERNAL_V2` canonical wire with exact signed64 tagged integer and source Unicode code-point preservation; no P5 implementation.
6. Minimal manual Streamlit Execute control, never triggering automatically upon rerender or restart.
7. P4-T01..T64 executable test cases, full F01..F38, X01..X19 and W01..W45 coverage, exact P0 P-A/P-B test-only logical projection, crash/restart and resource tests; test-only phase scoping of historical P3-T51 per CR-P4-001, retaining all negatives, plus P4-T62 whole-app audit.

## Constraints and failure discipline

- Preserve existing Streamlit monolith, one Python process, SQLite, local files; no migrations or additional production dependencies without owner-authorized CR.
- Forbidden: P5 final export/QA/round-trip, P6, more source types, branching/multiple datasets, networking or external marketplace actions, LLM transform/code execution, services/queues/workers, hidden conversions or new P0 statuses/operations/error codes.
- P4-Q05 bounded processing is not proved by design; full 100000x200, incremental RSS <=536870912 bytes and the approved 120-second soft-time policy require **actual Gate B measurement**. No silent memory/time workaround or partial output.
- Never weaken, skip or xfail earlier P0–P3 checks to make a build green. Any truly incompatible approved contract requires a documented Change Request presented to the owner, with no speculative implementation of the deviation.

## Delivery workflow

1. Codex starts from the current main and creates or checks out `feature/p4-deterministic-engine`; do not write P4 production code on main.
2. Validate approved ZIP SHA-256 before unpacking; read `SOURCES_AND_AUTHORITY.md` and full v1.0 contract/test pack, verify actual P1–P3 APIs before coding.
3. Implement P4 only, including required test-only CR-P4-001 correction; tests must have explicit oracles, no generic success-only assertions.
4. Run P4 64/64, P3 52/52, P2 54/54, P1 42/42 and P0 schemas/goldens; generate actual X13–X18 crash evidence, full load/metrics and whole-app audit. Report any NOT_RUN distinctly.
5. Produce `P4_GATE_B_VALIDATION_REPORT.md` with commit SHA, environment and commands, counts/pass/fail/skip/xfail, test IDs, golden/digest/canonical-wire outcomes, source integrity, RSS/time, crash/restart and known limits.
6. Present an **unmerged Draft PR** for independent review in the managing chat. Do not self-declare VALIDATED or merge/close Gate B.

## Acceptance authority

The owner has **authorized implementation start only**. Gate B must be independently reviewed and explicitly closed by the main managing chat after actual successful tests. Keep P4 stage `IN_IMPLEMENTATION` until that closure.
