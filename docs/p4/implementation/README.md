# P4 deterministic transformations — implementation interface

The owner-authorized P4 implementation consumes the unchanged P3 `P4Handoff` and current P1 Order CAS snapshot:

```python
from vde.execution.service import ExecutionService

service = ExecutionService(environment)
result = service.execute(order.id, order, handoff)
```

`start(...)` admits exactly one running Run and returns an internal active handle; `finish(...)` executes it. Admission re-reads exact version hashes/two immutable Approvals/source selection before source bytes. An explicit failed-run retry uses `fresh_handoff(order_id)` to reload the same P3 DTO fields and P1/P3 validation without changing frozen P3 APIs; stale EXECUTING or unhealthy workspaces cannot retry. Do not retain an active handle for restart recovery.

CSV/XLSX reads process every selected row using approved P2 options, SafeZip/cached-formula rules and source byte verification. Operations are the unchanged 12 P0 types. Stable sort/dedup use checked bounded ephemeral spill, not dataset tables or a full Python object matrix. Canonical V2 scalars preserve exact signed64/Decimal values and original Unicode code points. Approved CR-P4-004 corrects the Decimal regex for negative proper fractions; `-0`, exponents and trailing zeros remain invalid wire spellings.

One internal `P4_INTERNAL` / `P4_INTERNAL_V2` Artifact is published through frozen P1 Storage. A separate Run-success UoW completes delivery; Order remains EXECUTING. `read_result(run_id)` verifies complete ownership/versions/approvals/source/canonical bytes before read-only inspection. This is not P5 QA or export.

Open the existing Streamlit application, enable **Open deterministic transformation**, inspect source/selection/pipeline/limits, confirm and click **Execute**. Rendering/restart never initiates work. Health blocked/degraded disables execution. Run metrics/errors are read-only and no download/export/QA control is provided.

Validation: `.venv/bin/python tests/p4/run_validation.py` runs all 212 mandatory P1–P4 IDs and preserves upstream validation history, producing separate evidence under `docs/p4/validation/`. `tests/p4/build_scope_policy.py` builds an explicit reviewable source inventory; changes to this inventory require review, and cannot bypass frozen P0/P1/P2/P3 protection.

Owner-approved amendments: CR-P4-002 (T13 four source rows), CR-P4-003 (historical diff baseline only), CR-P4-004 (signed Decimal grammar). Immutable approved ZIP remains the design source, with these separately recorded exact amendments. Gate B requires independent main-chat review; implementation is not self-declared VALIDATED.
