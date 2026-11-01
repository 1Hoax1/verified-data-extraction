# P4 audit amendment v1.3 — approved CR-P4-005

Authority: owner-approved revised CR-P4-005, governance commit `f65e175708bc52058cbaf288d6953f2ac5ba5a50` and independently verified Stage A receipt in `docs/p4/validation/cr-p4-005/STAGE_A_APPROVAL_RECEIPT.json`. Original approved proposal/disposition and DECISIONS are unchanged.

The single active `tests/p4/approved_governance_pin_v1.json` identifies the exact DECISIONS Git commit/blob, SHA-256, length and mode. Its separate SHA-256 is fixed in the historical test verifier and P4 policy. The pin has no checksum of itself. DECISIONS contains none of its own final pin values. Ancestry and HEAD/stage-0 index/working bytes are verified without Unicode/newline normalization; obsolete content, staged/unstaged drift, wrong mode/type and missing/changed authority fail closed.

P2-T40 and P3-T51 keep their approved P4-start diff baseline and every original assertion/negative/ID. Only their positive changed/untracked audit calls gain explicit `root=ROOT`. Existing singleton DECISIONS negatives still fail. The path is not in a general allowlist.

P4-T61/T62 retain the independent full application, dependency/lock, frozen source/schema/pack/migration and forbidden-feature audits. The original DECISIONS baseline hash remains recorded; a separately verified CR-P4-005 exception, with no historical fallback, handles the approved document. Scratch probes require authority independently verified in the real checkout and exact copied bytes. P4-T63 still performs all 148 historical regressions and P0 checks.

P4-T62 additionally executes P01–P05 and N01–N14. Future receipt/repin behavior P05 is tested only in isolated synthetic Git history with a scoped test authority; no real new owner approval is asserted. N09 verifies the independent receipt comparison and retains the explicitly documented human review trust boundary. The other negatives exercise real file/index/commit/pin mutations in disposable copies, never the audited checkout.

Production bytes (including P4), schemas, fixtures, dependencies/lock, SQLite migrations, original packs and the 212 mandatory IDs are unchanged. The inventory builder verifies the exact two historical call-site substitutions and unchanged reviewed P4 source hashes before writing the new test-only inventory. New approval paths are enumerated exactly.

Any later DECISIONS byte change requires explicit owner approval of that version, a descendant governance commit, separate receipt and one updated pin/P/policy with full affected/combined regression. No new CR solely for checksum rotation is required under the approved procedure; content approvals and scope changes retain their normal requirements. No automatic latest-main selection or multiple accepted hashes.

Validation evidence is recorded separately without rewriting earlier logs. This amendment implements no Gate B closure or PR merge; the main managing chat remains the sole decision authority.
