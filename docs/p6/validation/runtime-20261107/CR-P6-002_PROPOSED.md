# CR-P6-002 — P-B acceptance semantics after legal UI identity adaptation

**Status: PROPOSED / NOT APPROVED / NOT IMPLEMENTED.** This is a request for a narrow owner decision; no P5 change is authorized by this document. P6 Gate B remains NOT CLOSED.

## Observed contradiction

P6 Design Pack v0.2 §9 expressly requires a UI-created UUID Order and legal in-memory identity/context adaptation of P0 fixtures, preserving their business semantics. Its P-B oracle requires READY / PASS_WITH_WARNINGS, six output fields, three rows, eighteen values and separate DQ-017 instances for PB-AC-006/007.

The frozen P3 `workflow/ui.py::draft` always assigns a fresh UUID to a newly published Brief. The frozen P5 `qa.py::evaluate_criterion` enables the approved PB-AC-002 five-column ordered-subsequence exception only when `context.brief.id == 'brief-pb-v1'`, in addition to the exact PB criterion/column shape checks.

Consequently, the real isolated P6 UI path with correctly adapted Order/asset identities and separately clicked test-user approvals produces an actual final XLSX and QA report, but PB-AC-002 follows generic five-versus-six sequence comparison. DQ-010 fails and Order is NEEDS_FIX / QA FAIL. P6-T06 and P6-T07 retain their strict required READY/PASS_WITH_WARNINGS assertions and fail. Their final exact-tree JUnit, complete report, identity substitutions and original/derived hashes are included alongside this proposal in the validation evidence.

This is not a historical scope conflict. It is a behavioral integration blocker involving protected P5 code and an approved P6 fixture adaptation. P-A and P-D are separate oracles and do not cure this failure. Correct XLSX cells alone do not turn failed business QA into PASS.

## Minimal proposed authorization

Permit one narrowly reviewed change to the P5 PB-AC-002 exception-recognition guard in `src/vde/p5/qa.py`, plus focused P6 regression assertions within the already authorized P6 test file. Do not change P0 canonical hashing, actual stored Brief/Spec IDs/hashes, approval linkage, report aggregation, QA IDs, transformations, old tests or certified fixture bytes.

Recognition should identify the exact approved P-B **business contract**, independent of legal generated version/Order/InputAsset identities. A concrete bounded option for review is a separate P-B template fingerprint: copy the Brief semantic payload solely for recognition, substitute only its already-validated selected input identity with the original canonical P-B template input identity, and compare the resulting P0 semantic hash to the approved P-B template hash `9b7c2b0111360714dfbc9cbdbc755b693b11e067f32771cb226126fdcd1ffb49`. Never mutate or replace the actual persisted document, its actual content_hash, source bytes or approval targets. Existing P5 admission must still verify the actual Order/asset/version/hash/Approval/Run context.

Retain all current PB-AC-002 guard details: exact criterion ID, COLUMNS/sequence_equals semantics, exact approved five target/expected columns, exact six output columns including line_total, and their order. The fingerprint option is a proposal, not an approved algorithm; the owner must approve its precise identity-normalization boundary before implementation.

Do not merely remove the Brief-ID check and recognize arbitrary contracts solely by a reusable criterion ID. Generic sequence_equals stays exact for every other business contract. No string/value normalization, alternate output, hidden column deletion, new operation or DQ check is introduced.

## Required positive and negative proof after approval

- Original certified P-B identity still yields the previously approved output/QA.
- A fresh UI-created Order, newly registered input, UUID Brief and separately approved published v2 with only legal identity/context substitutions yields READY/PASS_WITH_WARNINGS, one XLSX, 3×6/18 exact cells and both DQ-017 results PASS.
- P6-T06/T07 pass through the unchanged UI workflow and actual HTTP file readback.
- Arbitrary Briefs using PB-AC-002, altered objective/fields/criteria, five/six-column order changes, wrong target/expected/operator, missing line_total, mismatched source/context or unapproved versions do not acquire the exception.
- Generic sequence_equals remains exact; same-ID/different-content and different-ID/different-contract negatives fail.
- P-A, P-D, P0 validations, full phase-aware P1–P6 regression, protected-file audit and all original negative assertions remain intact. Any newly permitted P5 edit requires the owner's corresponding finite successor-audit amendment; no hidden historical hash or baseline changes.

## Rejected workarounds and unaffected limits

Do not force fixture IDs into the frozen UI, bypass P3 with prebuilt Approval records, alter PB-AC-002 to six targets only in tests, omit line_total, patch P5 from P6 at runtime, or classify this QA failure as an expected scope conflict. A newly versioned different P-B Brief/acceptance contract is a broader alternative requiring separate explicit owner design approval; it is not a silent fix.

No implementation of this proposal has been made. Changes remain confined to the originally approved P6 paths and exact four app lines. Actual Mac-host Docker smoke remains a separate NOT RUN environmental limitation; approval of this CR would not supply that missing evidence. Gate B closure, merge, governance changes and Pilot release remain owner decisions.

**Recommendation: APPROVE a precisely bounded identity-independent recognition rule, after independent review of its semantic fingerprint and negative boundaries. Until then: P-B E2E BLOCKED; preserve the real failures.**
