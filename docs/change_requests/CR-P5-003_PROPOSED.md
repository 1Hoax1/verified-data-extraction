# CR-P5-003 — Exact integer widening for approved decimal fields at the P4→P5 boundary

**Status: PROPOSED — NOT APPROVED / NOT IMPLEMENTED.**

Date: 2026-11-06 (Europe/Moscow). Repository: `1Hoax1/verified-data-extraction`.

P5 Gate A remains owner-closed `CLOSED / PASS`. P5 implementation was authorized; the affected numeric integration is now **BLOCKED pending this separate decision**. P5 Gate B is not closed. No P6 or merge is authorized by this proposal.

## 1. Authority and verified source

The owner approved Design Pack v0.2a, Supplement v0.2b, Q01–Q08, CR-P5-001 and CR-P5-002; original PROPOSED headings in those immutable sources are historical. This proposal does not question those approvals or amend them automatically.

- Pre-P5 historical base: `fd39aa1bed480313504ae8b1f76e77e170cb72ba`; tree `9d9f492491792a75b76954b3a17d1a376bc333e9`.
- Authorized P5 handoff HEAD: `d3f5d1898c9e90e08a5e518131e7f32d30b34a65`; tree `6946f1c52ed7b991f764573f69d15e1e50075906`.
- The source/runtime/tests are identical between those commits; the latter adds only the owner handoff anchor.
- The unchanged original 212 P1–P4 tests were freshly executed on the historical base: 42+54+52+64 PASS, zero failure/error/skip/xfail. This is not an integrated P5 validation claim.
- Independent real P1→P3→P4 fixture execution, with simulated user actions exclusively in disposable test databases, produced the observations below. No synthetic replacement P0 schema, input or P4 result was used.

## 2. Blocking mismatch

The normative v0.2a Q03 algorithm in `P5_V02A_NUMERIC_CONTRACTS.md` dispatches on the **actual decoded runtime type**: `type(value) is int` → integer ASCII; `type(value) is Decimal` → canonical coefficient with `.0` for integral Decimal. `DETERMINISTIC_QA_MATRIX.md`, DQ-011/016, requires exact declared types without implicit string/numeric coercion.

The approved P4 engine does not cast every final scalar to `Spec.expected_schema`. Its source adapter preserves integer XLSX `<v>` tokens as integer tags. Its `fill_missing` operation stores the approved scalar parameter unchanged, including the integer zero. The immutable P0 schema labels the following columns decimal:

| Fixture / output row | Column | Actual canonical P4 cell | Literal Q03 CSV | Frozen golden CSV |
|---|---|---|---|---|
| P-A / 3 | revenue | `{"type":"integer","value":"0"}` | `0` | `0.0` |
| P-B / 1 | unit_price | `{"type":"integer","value":"10"}` | `10` | `10.0` |
| P-B / 1 | line_total | `{"type":"integer","value":"20"}` | `20` | `20.0` |
| P-B / 2 | unit_price | `{"type":"integer","value":"20"}` | `20` | `20.0` |
| P-B / 2 | line_total | `{"type":"integer","value":"20"}` | `20` | `20.0` |

Observed full-file comparison using literal Q03:

| Fixture | Actual test-only projection | Immutable P0 reference |
|---|---|---|
| P-A | 275 bytes; SHA-256 `90295d6f974a564dd389de463912c4a0878c8ee000894e0553b5ae4c38d78d20` | 277 bytes; SHA-256 `c3b4e1f9a885bcf969cd34a9041951c1bed1abcd6aaba4c4f1f2fcd414d86cc9` |
| P-B | 237 bytes; SHA-256 `cd660986eddd4f1977ace62f9762dd94399111e2150bb3bdb6f40b6b142b94d9` | 245 bytes; SHA-256 `1e9449a8ff90f0cac9d62ba94b3d6e812dd565f85e9dd91fb2b48b6cbbf4d3c6` |

P-B CSV is only a test projection; production P-B remains one RESULT_XLSX. The same discrepancy affects strict decimal validation of the XLSX workflow even when its numeric cell value happens to be equal.

The read-only compatibility probe returns **exit 1**, with two failing contract-compatibility JUnit cases. These are **blocking semantic/contract mismatches**, not `EXPECTED_HISTORICAL_SCOPE_CONFLICT`.

Relevant frozen source: `src/vde/execution/source_adapter.py::_source_value`, `src/vde/execution/operations.py::apply_one` (`fill_missing`), and `tests/p4/test_execution.py::check_golden`. The latter already permits `int` or `Decimal` in decimal fields, but explicitly as a **P4 test-only projection**; it is not authority to extend production P5.

The approved numeric static verifier passes because `tools/verify_p5_v02a_precision.py::golden_oracles` reconstructs Decimal from golden CSV text. It does not consume actual P4 wire tags for these goldens. Thus static PASS and this integration FAIL are compatible observations.

## 3. Proposed minimal normative clarification

Approve an explicit P5-only, schema-directed, exact numeric projection at the verified P4 boundary:

1. Preserve canonical P4 bytes, tags, payload hash, immutable rows and original type evidence unchanged.
2. First validate every original tag with the existing P4 decoder and signed64/finite-Decimal guards. Noncanonical or corrupt tags still fail before export. A raw JSON number or a numeric-looking string is not a tagged integer.
3. For a selected, exactly approved `Spec.expected_schema` field with `data_type="decimal"`, permit **only** an original finite Decimal or an exact canonical signed64 integer. In the latter case form the P5 semantic/export view with `Decimal(original_int)`, using exact integer construction and **no float, quantization, rounding or source-text inference**.
4. DQ-011/016 explicitly treat that one widening as compatible with the approved decimal field. DQ-017 numeric comparisons and CSV/XLSX value checks use the exact semantic view, while null/missing and original wire-type evidence remain available. Never turn a typed null/empty string into a number.
5. CSV applies the existing Decimal spelling rule to that semantic decimal view: an integral decimal field emits `.0`. An approved integer field retains exact integer digits, even for the same mathematical value. This rule applies to any approved decimal field; it is not a fixture-name special case.
6. Approved integer fields remain strict integer-tag fields. Decimal→integer conversion, string→number parsing, bool→integer conversion, float recovery and all other new conversions remain forbidden.
7. XLSX retains the approved 15-significant-digit/magnitude admission and both exact numeric readback guards. Widening cannot bypass a precision rejection, silently write numeric data as text, or make a large signed64 numeric XLSX value acceptable.
8. No data-string NFC, trim, case change, scale recovery, new transformation operation, DQ ID, public error code or state is introduced. Existing approved header normalization remains separate.

This is a normative P5 clarification because the literal v0.2a runtime-type dispatch and strict DQ typing do not currently authorize the widening. Do not implement it merely as a formatting fix or assume approval from existing P4 test helper behavior.

## 4. Limited changes after explicit owner approval

Keep both approved ZIPs byte-identical. Publish a separate, versioned P5 addendum recording this authority and precedence over the affected Q03/DQ-011/016 wording; no replacement of historical pack bytes.

Implementation is confined to new P5-owned projection/QA/export/roundtrip modules and their P5 tests, plus the already approved minimal app integration. Proposed design paths are `src/vde/p5/project.py`, `src/vde/p5/qa.py`, `src/vde/p5/export.py`, `src/vde/p5/roundtrip.py`, and `tests/p5/`. Exact implementation inventory must be enforced by the CR-P5-002 successor audit.

No edits to P0–P4 production, schemas, original tests/fixtures, migrations, dependency/lock files, DECISIONS.md, G3 pin or old audit policy are requested. No repin, new governance trust mechanism, change to P3 Approval semantics or architecture is requested. Keep the approved implementation baseline unchanged.

## 5. Required acceptance after approval

Reuse the original 76 P5 test IDs; extend their cases without replacing required scenarios:

- P5-T21/T22 and T31/T32: exact signed64 tag in an approved decimal field passes only the explicit widening; numeric string, bool, float, noncanonical integer and Decimal→integer still fail. Null/empty and nullable/required policy unchanged.
- P5-T39/T40 and T55: actual unmodified P4 P-A handoff produces all six ordered headers, all cells and the exact 277-byte CSV hash, including original `integer:0` → approved decimal-field projection `0.0`. A changed scalar/tag/header must fail.
- P5-T33/T34/T56/T57: actual P-B wire retains quantity as integer, projects integer price/total as exact decimal semantics, checks full 3×6 and all 18 cells. Exactly one production RESULT_XLSX; the 245-byte CSV projection remains test-only.
- P5-T58/T62: P-D null/empty and duplicate failures still produce deterministic FAIL/NEEDS_FIX; the clarification does not repair data or force READY.
- P5-T64: CSV integer fields preserve `9007199254740991`, `9007199254740992`, `9007199254740993`, signed64 extrema exactly as integer digits. The same original tagged values in approved decimal fields widen exactly, but XLSX still rejects values outside its conservative bound; no binary64 intermediate. Integral Decimal and integer remain distinct when field types differ.
- P5-T72: both actual CSV/XLSX 100000×200 successful bounded runs remain mandatory. No stress acceptance is relaxed.
- P5-T73/T76: original 212 tests on frozen base, transparent compatibility probe on actual P5 tree, and negative-tested successor scope audit per CR-P5-002. No edits or blanket exemptions for old tests.
- Full available P0 schema/golden validation and unchanged-source hash checks. Original P-C missing-source limitations remain explicit.

CR-P5-001 remains binding: PB-AC-007 requires a new immutable Spec and its exact **real** local-user Approval in live workflow. A test-only/simulated Approval proves isolated mechanics only. This CR grants no such live approval.

## 6. Impact, alternatives and recommendation

This removes a numeric handoff blocker for the first actual P-A/P-B export while preserving exact values and the fixed architecture. It changes the P5 semantic projection/typing boundary, so owner review is necessary. Main risk: broadening the conversion beyond exactly approved decimal fields; mitigate with strict negative cases and retention of original wire evidence. No P1 API change is needed.

Alternatives: change P4 or P0 numeric fixtures/contracts (outside the authorized scope); alter frozen golden bytes (not acceptable here); reject the existing P-A/P-B result (honest fail-closed but blocks their mandatory positive acceptance). None is implemented.

**Recommendation: APPROVE only this exact, value-preserving P5 clarification. Until an explicit owner decision, CR-P5-003 remains PROPOSED and the affected implementation remains suspended.** No owner acceptance, P5 Gate B closure, merge or P6 authorization is asserted.

Evidence: `docs/p5/validation/implementation-admission-20261106/VALIDATION_REPORT.md`, `numeric-handoff/probe/NUMERIC_HANDOFF_FINDINGS.json`, canonical P4 wire snapshots and failing JUnit.
