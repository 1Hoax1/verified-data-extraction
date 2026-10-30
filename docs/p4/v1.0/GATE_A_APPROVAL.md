# P4 Gate A — Owner approval and design-gate closure

**Status:** CLOSED / PASS (design approval only).  
**Date:** 2026-10-30.  
**Decision revision:** `P4_GATE_A_APPROVED_2026-10-30`.  
**Owner authority:** explicit confirmation in the main managing chat, following strict v0.4.1 review.  
**Implementation start:** NOT_AUTHORIZED; P4 production implementation NOT_STARTED; future Gate B NOT_RUN.

## Approved source and immutable release identity

- Repository baseline: `411fda98b499646b355782d3ca3c34e20f9322ae` (main at independent review / approval).
- Exact candidate ZIP `P4_Implementation_Pack_v0.4.1_candidate.zip`: **SHA-256 `79f725fd96075f3ca87b6172819d82b557f5e373b1f5ebc46f08cfbe8b2e3d0a`**, **104894 bytes**; CRC PASS and 48/48 manifest payload size/SHA-256 PASS.
- Local **approved** ZIP prepared on 2026-10-30: `P4_Implementation_Pack_v1.0_APPROVED.zip`, **SHA-256 `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa`**, **112649 bytes**; CRC PASS, 53/53 payload size/SHA-256 PASS; all original 48 candidate payload files byte-identical. Its 5 additional files are approval/CR/strict-evidence/decision/assembly records, and a regenerated v1.0 approved manifest. No change to the reviewed engine/fixtures/test plan/verifier.
- **GitHub ZIP upload is PENDING.** This text decision records the owner approval and local verified approved artifact; it **does not imply the approved binary is present in GitHub**. Before separate implementation start, upload exact ZIP and verify Git blob size and SHA-256 against this record. See `docs/p4/v1.0/GITHUB_ARCHIVE_UPLOAD_PENDING.md`.

## Binding owner decisions

- **P4-Q01 APPROVED** — `ExecutionRun.succeeded` means durably committed P4 transform + internal Artifact, not P5 QA. Order remains `EXECUTING` until P5, stale `running` fail-closed, no auto-recovery.
- **P4-Q02 APPROVED** — missing field/null/empty/non-string behavior exactly as in candidate v0.4.1.
- **P4-Q03 APPROVED (revised)** — exact signed64 integer runtime and tagged-string `P4_INTERNAL_V2` wire, strict Decimal/date canonicalization and no hidden dataset Unicode NFC; existing P0 document hash/NFC exceptions preserved.
- **P4-Q04 APPROVED** — full-row verified P1/P2 read adapter, not the five-row preview; no frozen P1/P2 production change without CR.
- **P4-Q05 APPROVED conditionally on future Gate B evidence** — 100000 rows × 200 cols, sampled incremental +512 MiB RSS/120s soft time, bounded memory/spill policy, explicit P0 error codes; do not infer performance from P2.
- **P4-Q06 DEFERRED** — post-APPROVED revision disabled; CR-P3-001 remains DEFERRED.
- **P4-Q07 APPROVED** — test-only golden projection; no P5 export.
- **P4-D01..D14** adopted only as reviewed P4 design details consistent with above; **P4-D15 DEFERRED**.
- **CR-P4-001 APPROVED / NOT_IMPLEMENTED** — narrowly phase-scope P3-T51 historical inventory without deleting/skipping it or its negative checks; add P4-T62 whole-application audit with protected frozen P0/P1/P2/P3 runtime and forbidden-feature probes. Detailed disposition: `docs/change_requests/CR-P4-001.md`.

## Gate A actual evidence and limits

- Candidate v0.4.1 source CRC + payload manifest 48/48 PASS; approved ZIP CRC + payload manifest 53/53 PASS; unchanged 48 candidate files independently compared.
- Candidate P4 test-plan 64/64 test-specific oracle definitions; 38 F operation fixtures, 19 X exact failure postconditions, 45 W integer/JCS/Unicode precision oracles; 9/9 isolated verifier mutations correctly rejected.
- **Actual strict verifier PASS, exit 0**, reported by Codex on real checkout `411fda98b499646b355782d3ca3c34e20f9322ae` using Python 3.12.14 and jsonschema 4.26.0, command `python tools/verify_p4_fixture_consistency.py --p0-root "$REPO/pecs/pilot_slice_v1" --require-p0 --mutation-probes`. 36 P0 schema-valid, 2 schema-invalid rejected, 1 semantic-invalid identified, 2/2 P-A/P-B goldens, 9 mutation probes. See `docs/p4/v1.0/STRICT_VALIDATION_EVIDENCE.md`.
- Reviewing assistant independently reran static verifier and 9 probes against both candidate and locally assembled approved ZIP, **not** the full strict checkout verification.
- **P4 runtime and Gate B NOT_RUN:** none of P4-T01..T64 executed against production P4, no P1/P2/P3 live regression for P4, no full-workload engine RSS/time evidence, no crash/restart or P5 consumer implementation.
- Existing P0 PACK_MANIFEST discrepancy: 13/129 P-C approval-safety fixture paths absent in GitHub tree; P4 strict verifier checked its 17 actual required GitHub P0 files, not the complete P0 manifest. Keep this open as separate factual risk, no synthetic content or normative rewrite.

This Gate A closure **does not** authorize Codex implementation, adding dependencies, architectural changes, PR merge, P5 development, autonomous marketplace actions or P4 Gate B closure. **One next step:** complete approved ZIP GitHub upload and exact hash verification; then seek a separate explicit owner implementation-start authorization.
