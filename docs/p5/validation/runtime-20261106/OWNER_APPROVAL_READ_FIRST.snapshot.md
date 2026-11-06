# Owner decision: CR-P5-003 — APPROVED
**Decision date:** 2026-11-06
**Authority:** Express decision by project owner in the Main Managing Chat of Verified Data Extraction.
**Disposition:** APPROVED, effective only in the limits stated below.
**Source proposal:** `docs/change_requests/CR-P5-003_PROPOSED.md` (retain original historical PROPOSED label and bytes).
**Evidence:** `docs/p5/validation/implementation-admission-20261106/VALIDATION_REPORT.md`.
**Repo/branch:** `1Hoax1/verified-data-extraction` / `feature/p5-export-deterministic-qa`.
**Pre-decision HEAD:** `74050746d7fb2005a2178a719e5ee0b91d87fbf5`.

## Exact owner-approved scope

The owner approved the independent review of CR-P5-003 and expressly **APPROVED CR-P5-003**.

Allow **exact, lossless integer → Decimal widening at the P4→P5 boundary exclusively for a column whose *approved immutable TransformationSpecVersion* has `expected_schema[].data_type == "decimal"`**.

Conditions:
1. Widening occurs **only inside P5's semantic projection used for deterministic QA and export**. Do not mutate canonical P4 input/result bytes, original typed tags/values, checksums, immutable artifacts or execution history.
2. Decode and validate original P4 wire tags and signed64 bounds before any projection. Construct `Decimal(original_integer)` exactly, with no `float`, rounding, quantization, source-text guessing or other coercion.
3. Preserve strict integer-field typing. **Forbidden**: Decimal→integer, string→number, bool→integer, float recovery, silent null/empty conversion or any other new conversion. The approval is schema-directed; it is not fixture-specific or a general replacement for Q03.
4. Preserve existing CSV Decimal formatting and XLSX 15-significant-digit/magnitude plus exact round-trip/readback admission rules. XLSX may still fail closed for large integers/decimals; widening never bypasses numeric-precision rejection.
5. DQ-011/DQ-016 may regard the one approved exact widening as type-compatible for approved decimal columns; DQ-017 and export/round-trip use that exact P5 semantic view. Original wire-type evidence must remain accessible. Deterministic FAIL is authoritative.
6. Historical P0–P4 source, tests, fixtures, contracts, migrations, dependency/lock files, `DECISIONS.md`, governance pin and approved architecture remain unchanged.

## Required implementation sequence

**Before implementing the new numeric behavior, Codex must create a separate *versioned* P5 Design Pack addendum** recording the owner's authorization, exact normative precedence over the affected Q03/DQ-011/016 wording, acceptance conditions and traceability. Retain the original v0.2a and v0.2b ZIPs byte-for-byte. This decision record is **not itself** that versioned technical addendum.

After the addendum is saved, the owner **authorizes resuming P5 implementation** on `feature/p5-export-deterministic-qa`, within previously approved P5 Gate A, Q01–Q08, CR-P5-001 and CR-P5-002 limits.

Acceptance obligations unchanged: all **P5-T01…T76**, exact P-A/P-B/P-D outputs (P-B production XLSX only), real P-B v2 Approval for live operation (TEST_ONLY Approval never grants business authority), phase-aware historical **212-test** regression/evidence per CR-P5-002, available and required P0 schema checks, numeric negative checks, both CSV/XLSX **100000×200** successful bounded stress, recovery/idempotency/QA/state audits. Thirteen missing historical P-C files are not to be invented or reported as tested. Explicitly distinguish executed tests from pending tests.

## State and restrictions

- `CR-P5-003`: **APPROVED**.
- `P5 Gate A`: **CLOSED / PASS**.
- `P5 implementation`: **AUTHORIZED TO RESUME**, but **NOT YET VALIDATED**.
- `P5 Gate B`: **NOT_PASSED**; owner has not authorized closure.
- Merge to `main`, governance repin and P6 start: **NOT AUTHORIZED**.
- `docs/change_requests/CR-P5-003_PROPOSED.md` remains immutable as a historical proposal. This later owner disposition takes precedence **only for this exact CR**; do not infer any other approvals.

**Audit note:** This file is a recording of the owner's explicit in-chat decision, not a P3 business Approval, signature, merge permission, or replacement for immutable historical governance.
