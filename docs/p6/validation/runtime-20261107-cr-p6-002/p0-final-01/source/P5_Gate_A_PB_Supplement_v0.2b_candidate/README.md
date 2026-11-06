# P5 Gate A completion — versioned P-B supplement v0.2b (CANDIDATE)

**Normative baseline:** main `fd39aa1bed480313504ae8b1f76e77e170cb72ba` + independently reviewed P5 Design Pack v0.2a.  This is a *delta*, not a wholesale rewrite.

**Authority:** owner APPROVED Q01…Q08 and CR-P5-001 in Main Managing Chat; authorized preparation of versioned fixtures, traceability and static checks **only**. Original CR proposal and P0 fixtures have not been rewritten.

**Contents:** new immutable SpecVersion v2 candidate, test-only exact structurally bound Spec Approval, explicit approval request (pending *real* user action), versioned oracle, version-bound test-only QAReport (24 checks), traceability, owner decision record, static verification and manifest.

**Critical distinction:** `transformation_approval_v2_TEST_ONLY.json` uses an obviously synthetic future date (`2099-01-01T00:00:00Z`). It is **not real** Approval of the new Spec. Its positive P5 test may run only in isolated fixture context; a real current-order positive PB-AC-007 remains blocked until explicit local-user Approval. Do not import the synthetic record as real business data.

No code, GitHub commits, production P1–P4 files, P0 originals, fixtures or approved goldens changed. No P5 runtime tests run.

**P5 Gate A NOT_PASSED**; separate owner gate closure still required.

## Reproducible static verification

Unpack the unchanged v0.2a base archive separately, then from this supplement folder run:

```sh
python tools/verify_gate_a_supplement.py --base-root /path/to/P5_Implementation_Design_Pack_v0.2a_candidate --mutations
```

The verifier checks the **60-file original base manifest**, P-B Spec v1 source semantic SHA-256, new Spec v2 hash and permitted delta, exact synthetic Approval binding, proposed DQ oracles and 12 negative mutations. The original P0 schemas were not staged in this ZIP; a full P0 JSON Schema validation is not claimed.
