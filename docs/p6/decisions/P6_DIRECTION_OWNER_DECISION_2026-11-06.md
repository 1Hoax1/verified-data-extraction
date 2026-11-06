# P6 direction — owner decision (2026-11-06)

**Authority:** explicit response «принимаю» in the Main Managing Chat to the P6 Design Pack v0.1 direction/recommendations; recorded here as project guidance, **not** as Gate A closure or authorization to implement.

## Approved direction
- Complete Pilot Slice V1 only via local Streamlit Create Order → existing P2 input → human-reviewed BriefVersion and separate human-reviewed TransformationSpecVersion with both independently recorded Approvals → explicit deterministic P4 → explicit P5 export/QA → verified Result/QAReport download. No direct SQLite editing by the ordinary user.
- P6-Q01 **APPROVED:** supported runtime Linux; Mac only via local Linux container. Native macOS portability changes require separate CR.
- P6-Q02 **APPROVED:** resource-bounded result/report downloads, actual runtime measurement, fail-closed when limits cannot be met, no silent reduction of approved workload.
- P6-Q03 **APPROVED:** preserve the existing P3 JSON editor within Streamlit; no new form builder.
- Scope excludes LLM, Telegram, new transforms/DQ IDs, URL ingestion, browser automation, marketplace login, automatic outbound delivery, new user roles/states and edits to frozen P1–P5 business logic.

## Later approved exception (separate decision)
CR-P6-001 **APPROVED** subsequently by the owner, separately recorded at `docs/p6/decisions/CR-P6-001_OWNER_DECISION_2026-11-06.md` (commit `4e1559c99817d16b842c81010ce528e191a14795`). This allows only the frozen P6 path inventory, an exact four-line `app.py` extension and a successor P6 audit. It does not revise this historical direction.

## Current gates
P5 `VALIDATED/MERGED` at merge SHA `0af4a1ff49ccf8fa59c39780d749e15cb5042fc3`; P6 Design Pack v0.2 remains **PROPOSED** until separate Gate A approval. `P6 Gate A: OPEN`, `P6 implementation: NOT STARTED`, `P6 Gate B: NOT PASSED`, `Pilot release: NOT AUTHORIZED`. No P6 source or test runtime added by this record.

---

## Later explicit owner decision — P6 Gate A CLOSED / PASS (2026-11-06)

**Authority and context:** The owner in the project's Main Managing Chat answered «ок, утверждаю» to the explicit request to approve closure of **P6 Gate A: CLOSED / PASS** after the independent static design review. This approval is separate from the earlier directional approval and from the previously approved CR-P6-001.

**Disposition:**
- **P6 Design Pack v0.2: APPROVED** for Pilot Slice V1 P6, exactly the candidate published at `docs/p6/design/P6_DESIGN_PACK_v0.2.md`, Git blob `50b744540bbac136469565d1f9af57ab81697786`, independently reviewed design SHA-256 `c4b09611a647524678882c4f0b1d28a6cad1d3b8ff0c0ee0a04b92ca220dd8e0`.
- **P6 Gate A: CLOSED / PASS** by the project owner, relying on **29/29 PASS, 0 FAIL** in the independent *static design review*, recorded in the Main Managing Chat as `P6_GATE_A_STATIC_REVIEW_2026-11-06.md` and the machine-readable companion JSON; these are conversation evidence, not represented here as a GitHub test run.
- **P6-C01…C05:** approved design contracts with defined input/output, states, errors, readiness and test scenarios. **P6-T01…P6-T20:** approved acceptance oracles and fixture/error-policy coverage; **none of these 20 P6 runtime tests has been executed by this decision**.
- The previously approved **CR-P6-001** finite scope, four-line UI hook exception and phase-aware successor audit rules remain unchanged. The earlier `## Current gates` paragraph above is historical status *before* this explicit later closure; the present dated decision supersedes only the Gate A/design approval status, not the preserved scope and limits.

**Boundaries and known limitations retained:**
- Frozen baseline `main:0af4a1ff49ccf8fa59c39780d749e15cb5042fc3`; P1–P5 must not be modified outside the exact four-line `src/vde/app.py` integration exception.
- Maintain human-only two real business Approvals; deterministic QA authority; no LLM, new operations, browser/exchange automation, new schemas, migrations, dependencies or silent repair.
- Thirteen missing P-C historical originals are not assumed tested; existing P5 scope assertions can register genuine historical-scope FAIL on P6 and require explicit phase-aware classification; do not claim them PASS.
- Linux is the approved runtime (macOS via local Linux container, not native); bounded verified-byte snapshot delivery is approved with an explicit last-browser-click limitation.

**Unchanged downstream statuses and prohibitions:**
- `P6 implementation: NOT STARTED`; **start of implementation/Codex coding requires a separate explicit authorization**.
- `P6 Gate B: NOT PASSED`; `Pilot release: NOT AUTHORIZED`.
- This does **not** authorize merging P6 to `main`, changing the governance pin, releasing Pilot, or commencing any new phase.

**Next action:** issue a separate explicit owner authorization to implement the *approved P6 Design Pack v0.2* under *CR-P6-001*, after which Codex may implement only the finite list and execute the mandated runtime acceptance and regression tests.

**Audit:** This is a project gate decision, not a P3 business Approval, runtime validation report, or self-approval by a code agent.
