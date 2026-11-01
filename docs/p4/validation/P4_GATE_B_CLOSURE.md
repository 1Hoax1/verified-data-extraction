# P4 Gate B — owner closure / PASS

**Status:** CLOSED / PASS (owner-confirmed 2026-11-02).  
**P4 validated scope:** immutable tested integration implementation — not yet merged to main.  
**Decision register:** `DECISIONS.md` section `P4 — Owner closure of Gate B (2026-11-02)`.  
**Merge authorization:** NOT_GRANTED; a final Draft integration PR is authorized.

## Validated identity and published evidence

- Tested commit: `a868134fb9f3118bd5e56c26662db55fe281430d`.
- Tested tree: `0150b2eccb498d86b6e0ecf2cbc854a6de381f39`.
- Evidence-only child commit: `a3cc40d6ea4d97d118dabee577d24c47811518c1`.
- Full evidence folder: `docs/p4/validation/cr-p4-005/stage-b/` on the evidence child branch.
- Published `STAGE_B_VALIDATION_REPORT.md`, JUnit XML, stdout/stderr, per-case status, pin mutation evidence, resource/load metrics, code/test baseline hashes, 121-entry original and 125-entry publication manifests.
- Independent file identity audit: all 122 original evidence files matched the GitHub repository blobs byte-for-byte; no production or test change in evidence publication.

## Gate B actual results

| Gate | Observed result |
|---|---|
| P1 | 42/42 PASS |
| P2 | 54/54 PASS |
| P3 | 52/52 PASS |
| P4 | 64/64 PASS |
| Total | 212/212 PASS; fail/error/skip/xfail = 0 |
| P2-T40 / P3-T51 integration | 2 PASS |
| P4-T61/T62/T63 audit/frozen | 3 PASS |
| P01–P05 and N01–N14 | 19 PASS / 59 subcases |
| F38 / X19 / W45 | ALL PASS |
| P0 goldens and strict fixture verifier | PASS; 9/9 mutations rejected |
| Failure/restart/rollback | PASS according to preserved execution evidence |
| Capacity, 100000 × 200 | PASS; 90000 × 200 output and 18 million verified cells |
| Runtime | 58.054262 sec (soft target <=120 sec) |
| Incremental peak RSS | 293617664 bytes (limit <=536870912) |

All runtime tests refer to the **tested commit/tree above**, and were not rerun on the evidence-only child. Independent review checked persisted evidence but did not reproduce the entire suite on another host.

## Approved CRs and boundaries

- CR-P4-001…005: implemented and technically validated on the tested integration snapshot, within exact owner-approved boundaries.
- P4 success is durable internal transform/Artifact; Order remains EXECUTING pending P5 QA. P4 validation does not implement P5.
- No P0/P1/P2/P3 production change, unapproved operation, schema/migration, dependency or automation feature.
- Known limits: Linux/Python3.12 evidence, no cross-host/Windows/CI proof, sampled RSS/soft time, AppTest instead of manual browser, open P0 P-C 13-file discrepancy.

## Owner closure vs final integration

This document **closes Gate B for the tested P4 implementation**, but does not declare P4 merged to `main` and does not authorize merge.

The owner also authorized preparation of a final **Draft integration PR**. The existing Draft PR #4 points at a pre-CR-P4-005 head and must not be merged as-is.

**CR-P4-005 governance repin requirement:** This closure changes `DECISIONS.md`. Freeze and publish the new immutable governance-only approval commit `G2`, then compute `G2/B2/H2/L2/M` from that commit's `DECISIONS.md` Git blob and publish a separate receipt outside DECISIONS. Thereafter Codex may update the pin/P/audit policy and evidence under the already approved *limited repin* procedure, with the full final-tree regression and negative checks. No additional CR is required solely for hash rotation.

A final merge requires a **separate explicit owner authorization**, verified integrated history and a fresh 212/212 test pass tied to that exact final combined tree.

## Next action

Prepare an unmerged final Draft integration PR; request test-only pin rotation and combined-tree validation before merge.
