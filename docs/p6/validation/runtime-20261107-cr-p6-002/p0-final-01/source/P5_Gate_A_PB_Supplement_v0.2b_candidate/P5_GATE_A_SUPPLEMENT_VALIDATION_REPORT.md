# P5 Gate A — limited P-B fixture completion static validation report

**Date:** 2026-11-05. **Scope:** P5 v0.2a → design-only P-B v0.2b candidate supplement. **Status:** `STATIC_DESIGN_PASS / GATE_A_NOT_PASSED`.

## Authority and protection

- Project owner **APPROVED** Design Pack v0.2a review, Q01…Q08 and CR-P5-001 with six limiting conditions in Main Managing Chat. This file records the decision; it does **not** close Gate A or issue a live P3 Approval.
- GitHub base main was independently checked unchanged at `fd39aa1bed480313504ae8b1f76e77e170cb72ba`.
- P0 original fixtures, existing Q decisions, base v0.2a, P1–P4 and `main` untouched; all new design files live only in this local supplement ZIP.
- **No P5 production-code implementation, GitHub commit/merge, P6 or runtime execution** was performed.

## Versioned P-B fixture

- Original P-B Spec v1 immutable semantic payload independently reconstructed from GitHub source. Recalculated using Unicode NFC + canonical JSON for this **integer-only numeric payload**; digest **`d7c30e08e6d03054d4a15daeb741f64c1f4fef64c225208d98c1659f8e82f2aa`**, exact equality with approved P0 content hash.
- Proposed immutable P-B TransformationSpecVersion: `transform-pb-v2-cr-p5-001`, version number 2, content hash **`c4f9aa33b341cf703b8edacbe60ba1b8070814dde461b4412407d8535188c9a3`**. Only semantic change: append `PB-AC-007` to `acceptance_criteria_ref`; all other semantic fields equal v1.
- P-B output remains 3×6 in XLSX; DQ-022 demands six headers and all 18 cells; PB-AC-002 locally checks only the five ordered names (generic `sequence_equals` unchanged).
- The version-bound **TEST_ONLY** QAReport specimen has 24 check entries, 23 distinct DQ IDs and one RESULT_XLSX reference; no P5 runtime evaluated it.
- DQ-017 occurs twice: (`PB-AC-006`, `quantity`, minimum 1), (`PB-AC-007`, `line_total`, minimum 0).
- `transformation_approval_v2_TEST_ONLY.json`: syntactically aligned with P0 Approval fields and exact new Spec id/hash/Brief context. Its deliberately future timestamp **2099** identifies it as **synthetic test fixture, not a real human/local user approval**. The `approval_request_v2_PENDING.json` cannot pass as an Approval and records the unissued exact live Approval. The PB-AC-007 positive *approved-context* test is blocked until a real Approval is issued in the appropriate scenario.

## Actual static executions

| Command (from source root) | Actual result |
|---|---|
| `python tools/verify_p5_design_pack.py --mutation-probes` from unchanged v0.2a base | exit 0; **4/4 negative mutants rejected** |
| `python tools/verify_p5_v02_amendments.py --mutation-probes` from unchanged v0.2a base | exit 0; **9/9 negative mutants rejected** |
| `python tools/verify_p5_v02a_precision.py --mutation-probes` from unchanged v0.2a base | exit 0; **26 numeric cases; 14/14 negative mutants rejected**; P-A/B exact CSV goldens PASS |
| `python tools/verify_gate_a_supplement.py --base-root /path/to/unpacked/v0.2a --mutations` from this supplement | exit 0; **60/60 v0.2a baseline manifest entries verified; 15/15 negative mutants rejected**; v1/v2 hashes, versioned refs, test-only Approval binding PASS |

Artifacts: full stdout, stderr and exit codes saved under `validation/`; exact verifier sources in `tools/`. All original v0.2a suite test IDs **76** remain unchanged (not executed as P5 runtime tests).

**Aggregate explicitly executed static negative mutation probes: 42 rejected (4+9+14+15).** These are not real P5 runtime scenarios and must not be counted among 76 P5 tests.

Environment: Python `3.13.5`, jsonschema `4.26.0`, openpyxl `3.1.5`. Exact v0.2a ZIP source SHA-256: `a351fb55c5ea3d442cc3ff3e3facc7a09c426569aad476fb713f8f09f10ca3ac`.

## Not run / non-claims

- P5 runtime 76 scenarios: **NOT_RUN**. P1–P4 212 regression in P5 environment: **NOT_RUN**.
- Complete original P0 JSON Schema validator at the pinned source: **NOT_RUN** (not staged in the present local supplemental ZIP). Existing schema shape, Approval field names and version patterns were additionally inspected through the GitHub connector. No claim of full runtime P0 schema conformance.
- P-C original approved source has **13 missing manifest files**; no fabricated replacement. Available-only negative tests and original P0 preservation remain binding.
- P-B actual exported XLSX, resulting SHA/bytes, and concrete user's new P3 approval: **NOT_RUN / NOT_ISSUED**. The P0 XLSX golden remains the historical artifact; supplement does not produce a new export or modify it.
- No physical restart/power-loss, memory stress 100000×200, CI, Windows validation; those belong to Gate B.

## Recommendation for managing chat

**Design-only supplement: ACCEPT FOR GATE A OWNER REVIEW**, not automatically validated runtime and not Gate A closure. Before closing Gate A, owner must inspect the v2 Spec SHA and approve the fixture binding semantics explicitly; distinguish future real local P3 Approval from test-only specimen. P5 implementation remains **NOT_AUTHORIZED** unless explicitly authorized separately after Gate A closure.
