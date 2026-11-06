# P5 Design Addendum v0.2c — CR-P5-003 exact semantic widening

Version: **0.2c**, 2026-11-06. Status: **OWNER-APPROVED RULE / IMPLEMENTATION AUTHORIZED; runtime validation pending**.

Authority: [CR-P5-003 owner decision](../decisions/CR-P5-003_OWNER_APPROVAL_2026-11-06.md) at immutable commit `820245fc544fc66c393db548151e6d281e03d414`, explicitly approved in the Main Managing Chat. The historical [proposal](../../change_requests/CR-P5-003_PROPOSED.md) and its failed admission evidence remain unchanged. This technical addendum records the authorized rule; it does not supply a P3 business Approval or close a release gate.

## Precedence and unchanged inputs

Apply Design Pack v0.2a and P-B Supplement v0.2b as approved by the owner. This addendum takes precedence **only** over the affected Q03 runtime-type dispatch and DQ-011/DQ-016 strict decimal-type wording where a verified canonical signed64 integer occupies an approved decimal field. All other Q01–Q08 requirements, CR-P5-001 and the phase-aware CR-P5-002 protocol remain binding. The original ZIP bytes and manifests are unchanged.

- Design v0.2a ZIP SHA-256: `a351fb55c5ea3d442cc3ff3e3facc7a09c426569aad476fb713f8f09f10ca3ac`.
- Supplement v0.2b ZIP SHA-256: `4e08285b00344f2d00a7af89a723a835f931f4bceb768b11ec1aaf637fd0ae18`.
- Historical regression base: `fd39aa1bed480313504ae8b1f76e77e170cb72ba`; existing governance authority and implementation baseline are unchanged.

## Normative algorithm

1. Revalidate the exact approved Order/Run/Brief/TransformationSpecVersion/Approval/source context and canonical P4_INTERNAL_V2 bytes using existing P1/P3/P4 guards. Original scalar tags must pass canonical spelling, signed64 bounds and finite-Decimal checks **before projection**. No type is guessed from source text or JSON numbers.
2. Build a separate row-local P5 semantic view, in approved `Spec.output.column_order`. For the immutable selected Spec's `expected_schema[].data_type == "decimal"` only, if `type(original) is int`, construct **`Decimal(original)`** exactly. Existing finite Decimal stays Decimal. Preserve null, empty text and every other original value without conversion. No float intermediate, rounding, quantization or context-dependent normalization is permitted.
3. All other field types retain strict typing. Decimal→integer, bool→integer, string→number, float recovery and any other new conversion remain forbidden. An invalid value may be represented in a diagnostic export, but its typed DQ failure remains authoritative; it must never acquire QA PASS by coercion.
4. DQ-011/DQ-016 use the exact projected view for the approved decimal field, with original canonical P4 data/type evidence still accessible through the immutable internal Artifact. DQ-017, numeric export and full readback compare the same exact semantic view. Null/empty checks use the unchanged null/empty values. Preserve P4 bytes, tags, checksum, metrics, Run and artifact history.
5. Q03 CSV spelling is unchanged **after** projection: integer fields use exact integer ASCII; decimal fields use canonical finite Decimal coefficient plus `.0` for integral Decimal. Thus integer field `10` emits `10`, decimal field receiving original integer `10` emits `10.0`. No original display scale is recovered.
6. XLSX preserves 15-significant-digit/conservative magnitude admission, explicit text cells, independent XML numeric-lexeme and openpyxl readback checks. Exact widening never authorizes unsafe XLSX precision, numeric-as-text substitution or formula interpretation. Existing fail-closed codes and state rules remain unchanged.
7. No implicit NFC, trim, case change or other transformation of data strings. Only the already approved output-header metadata normalization is applicable.

## Acceptance and traceability

| Requirement | Existing test IDs / evidence |
|---|---|
| Exact signed64→Decimal only in approved decimal field; strict negative conversions | P5-T21/T22, T31/T32, T64 |
| Actual unchanged P4 P-A zero tag produces full 277-byte CSV golden | P5-T39/T40, T55 |
| Actual P-B integer price/total tags; six columns, 18 cells, two approved criterion instances in isolated v2 test context | P5-T33/T34, T56/T57 |
| P-D nulls/duplicates remain FAIL→NEEDS_FIX with diagnostic CSV | P5-T58/T61/T62 |
| Signed64 extrema, 2^53 boundaries, Decimal precision and XLSX rejection | P5-T39/T40, T64 |
| P4 bytes/tag/checksum, contracts/tests/migrations/dependencies/governance frozen | P5-T73/T76; successor P5 audit and mutations |
| Real CSV and XLSX 100000×200 successes, full 20M-cell comparisons and sampled RSS ≤536870912 each | P5-T72 |
| Complete 76 runtime IDs, separate historical 212 base and integrated compatibility outcomes | CR-P5-002 external validation runner |

P-A and P-B production must consume actual P4 output, not regenerated Decimal tags or synthetic replacements. P-B production remains one RESULT_XLSX; CSV remains test-only projection. PB-AC-007 needs its exact new Spec and real local-user Approval in live use; isolated simulated approvals never grant live authority. Original missing P-C files remain explicitly unavailable. No P0–P4 edits, dependency or migration changes, governance repin, merge or P6 are authorized.

This addendum was saved and committed before implementing the newly approved numeric rule. P5 Gate B remains owner-controlled and NOT_PASSED until a separate owner decision.
