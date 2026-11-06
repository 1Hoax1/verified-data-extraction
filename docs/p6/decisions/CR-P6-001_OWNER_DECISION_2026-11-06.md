# Owner decision — CR-P6-001: APPROVED (finite P6 scope + phase-aware validation)

**Decision date:** 2026-11-06.
**Authority:** project owner, Main Managing Chat, in response to the request for a separate decision on `CR-P6-001_REVISED_CANDIDATE.md` and P6 Gate A v0.2: «давай примем лучшее решение тогда». The assistant recommended the narrowly bounded **APPROVE** and confirmed that decision to the owner.
**Disposition:** **APPROVED**, only for the exact exception stated here; does **not** close P6 Gate A or authorize implementation.
**Frozen baseline:** `main:0af4a1ff49ccf8fa59c39780d749e15cb5042fc3` (P5 PR #7 merge).
**Original CR proposal:** `CR-P6-001_PROPOSED.md` prepared in the Main Managing Chat; original historical PROPOSED draft is preserved unchanged, and the revised owner-reviewed candidate is `CR-P6-001_REVISED_CANDIDATE.md` (2026-11-06). Those local proposal artifacts are not evidence of implementation.

## Current immutable rules

Approved P0–P5 scopes, source, tests, fixtures, P0 schemas, migrations, dependencies/lock, `DECISIONS.md`, G3 pin, and historical runtime evidence remain immutable. The exact P5 successor audit/policy rejects additional P6 source files and any further `app.py` UI append. Do not rewrite or disable `P5-T76`, replace prior validation evidence, or interpret former phase-scoped checks as passing the extended P6 tree.

## Narrow permission granted (closed inventory)

**New runtime files — four:**
1. `src/vde/p6/__init__.py`
2. `src/vde/p6/orders.py`
3. `src/vde/p6/delivery.py`
4. `src/vde/p6/ui.py`

**New test/runner/audit files — six:**
1. `tests/p6/__init__.py`
2. `tests/p6/conftest.py`
3. `tests/p6/test_acceptance.py`
4. `tests/p6/scope_audit.py`
5. `tests/p6/scope_policy_v1.json`
6. `tests/p6/run_validation.py`

**New design/decision/release files — five:**
1. `docs/p6/design/P6_DESIGN_PACK_v0.2.md`
2. `docs/p6/decisions/P6_DIRECTION_OWNER_DECISION_2026-11-06.md`
3. `docs/p6/decisions/CR-P6-001_OWNER_DECISION_2026-11-06.md` (this record)
4. `docs/p6/README_PILOT.md`
5. `docs/p6/RELEASE_CHECKLIST.md`

**New evidence:** only under `docs/p6/validation/runtime-*/`, with finite file inventory, SHA-256 manifest and exact tested SHA/tree, commands, environment, raw JUnit/outcomes, negative probes and observations.

**The only authorized edit to an existing source file** is exactly four added lines in `src/vde/app.py`, preserving all other lines and their order. Before the existing `from vde.ingestion.ui import panel`, insert:

```python
from vde.p6.ui import order_panel
order_panel(result)
```

Immediately after the existing final `export_qa_panel(result)`, insert:

```python
from vde.p6.ui import delivery_panel
delivery_panel(result)
```

This is an exact UI hook exception, **not** permission to edit the old P1–P5 panels. No other source, test, policy, schema, fixture, migration, dependency, governance, or evidence bytes may be changed without another approved CR.

## Permitted functional boundary

P6 only: create a DRAFT Order via the existing P1 repository; reuse manual P2–P5 UI and the original two independent human Approvals unchanged; expose verified terminal result or explicitly labeled NEEDS_FIX diagnostic and matching QAReport downloads; implement read-only restart/corruption inspection, Linux/Mac-container instructions, and release checklist. Do not add LLM, Telegram, exchange automation, API, network backend, new operations, state transitions, approval roles, or P0 error enums.

## Phase-aware validation obligations

1. Pin and verify the entire baseline `main:0af4a1ff49ccf8fa59c39780d749e15cb5042fc3` (all old blobs/file modes), exact four-line `app.py` exception and the finite new-file list. Do not silently modify historical baselines.
2. Execute and report **all P6-T01…T20** on the actual P6 implementation tree. P6-T18 must contain the successor audit and negative mutation checks. No synthetic claims of runtime success.
3. Preserve and separately cite P1–P4 **212/212** and P5 **76/76** on their actual approved historical/implementation trees, and execute the unmodified legacy/P5 suites on the new P6 tree, recording **every actual PASS/FAIL and raw JUnit**.
4. The original P5-T76 on P6 source may FAIL on P6 file inventory. Classify only failure assertions proven to result from owner-approved new P6 scope as historical scope conflicts, and retain genuine FAIL outcomes (no skip/xfail or false PASS). Any other behavioral regression blocks Gate B.
5. Test real P-A/P-B/P-D E2E, available P-C negatives without inventing the 13 missing originals, verified byte/hash output, UI-only order creation/idempotency, cross-order confidentiality, memory-bounded Streamlit download, restart/corruption fail-closed.
6. P6 UI diagnostics must not introduce new P0 `ExecutionError` enum values. Existing deterministic QA and human approval decisions remain final.

## Known risks and limits

- Streamlit download caches an immutable verified byte snapshot in session; it cannot guarantee reread on the browser's last transfer click. Verify at a separate explicit prepare action and invalidate on selection/context changes; memory allocation may fail closed. No unsupported memory guarantee or untested 100000×200 browser-download claim.
- Native macOS P2 memory check uses Linux `/proc`; supported Pilot runtime is Linux, including Linux in a local Mac container. Native macOS portability is outside this CR.
- Existing 13 missing P-C originals are not fabricated; phase-specific scope conflicts are not marked as PASS.

## Consequences, statuses, next gate

- **`CR-P6-001: APPROVED`** only for the finite exception above.
- **`P6 DESIGN DIRECTION: APPROVED`** (previous owner decision).
- **`P6 Design Pack v0.2: PROPOSED`**, its contracts/fixture inventory/error policies still require independent static review and explicit Gate A approval.
- **`P6 Gate A: OPEN / NOT APPROVED`; `P6 Implementation: NOT STARTED`; `P6 Gate B: NOT PASSED`; `Pilot release: NOT AUTHORIZED`.**
- No merge, governance repin, or P6 code authoring is approved by this decision.
- **Next one action:** finalize and independently check `P6_DESIGN_PACK_v0.2` with C01–C05, exact 20 test oracles, fixtures/error policies and resource controls; bring Gate A closure to the owner for a separate decision.

This record is only an explicit project scope decision, not a P3 business Approval, an implementation certification, or permission for automatic customer delivery.
