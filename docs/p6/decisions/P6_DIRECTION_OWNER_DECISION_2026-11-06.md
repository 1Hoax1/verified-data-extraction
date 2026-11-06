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
