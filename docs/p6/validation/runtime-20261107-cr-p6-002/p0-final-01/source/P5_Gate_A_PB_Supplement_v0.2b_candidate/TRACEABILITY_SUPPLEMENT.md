# P5 Gate A — P-B versioned fixture traceability (supplement to v0.2a)

Base design: `P5 Implementation Design Pack v0.2a`, **unchanged**, pinned main `fd39aa1bed480313504ae8b1f76e77e170cb72ba`.

| Requirement / approval basis | New evidence | Tests / oracle | Permission / state |
|---|---|---|---|
| Six-column XLSX / output contract | `transformation_spec_version_v2_CANDIDATE.json`, `p_b_versioned_oracle_candidate.json` | P5-T56/T57: one `RESULT_XLSX`, 6 columns; CSV test-only | P5 Q01/Q02, CR-P5-001 APPROVED; runtime NOT_RUN |
| `PB-AC-002` five selected ordered column names | `p_b_versioned_oracle_candidate.json` / `pb_ac002` | P5-T19/T20: selected ordered subsequence; full six independently checked | **P-B only**; generic `sequence_equals` unchanged |
| DQ-022 full roundtrip | `p_b_versioned_oracle_candidate.json` / `dq022`; `qa_report_specimen_v2_TEST_ONLY.json` | P5-T39/T40: 3×6, six localized headers, 18 typed cells, no formulas | Runtime NOT_RUN |
| `PB-AC-006`, one DQ-017 | New v2 refs, `dq017[0]` | P5-T33/T34: quantity min=1 | Original Spec v1 already references 006 |
| `PB-AC-007`, second DQ-017 | New v2 ref, `dq017[1]`; version-bound 24-check QAReport specimen | P5-T33/T34/T74: line_total min=0; reject if not approved | Test-only proposed Approval; **real Approval PENDING** |
| New immutable Spec content hash | `transformation_spec_version_v2_CANDIDATE.json` | Verify canonical semantic payload SHA-256 `c4f9aa33b341cf703b8edacbe60ba1b8070814dde461b4412407d8535188c9a3` | Exact version+hash, original v1 unchanged |
| Exact Approval binding | `transformation_approval_v2_TEST_ONLY.json`; `approval_request_v2_PENDING.json` | Verify target_version/hash and Brief context; reject wrong target/hash | Synthetic **TEST_ONLY**, not permission to execute actual Order |
| P-B test-only CSV projection | v0.2a historic CSV SHA and CR local rule | P5-T56/T57: registered Result CSV count=0 | One production XLSX |
| Q03 CSV Decimal, Q04 XLSX numeric | v0.2a `P5_V02A_NUMERIC_CONTRACTS.md` unchanged | Existing P5-T63/T64 + precision unit cases | Approved design, future runtime NOT_RUN |
| P-C historic missing files | v0.2a `fixtures/p0_pc_reachability_v02.json` unchanged | P5-T59/T66/T74 available negatives; full positive BLOCKED | 13 certified missing files unchanged |
| Gate B full P1–P4+P5 and stress | v0.2a GATES.md unchanged | 212 P1–P4 + 76 P5; successful CSV and XLSX fixed 100000×200 | Runtime NOT_RUN, Gate B blocked until implemented |

No existing P5-T IDs or DQ IDs are modified. Positive `PB-AC-007` must **never** be labelled approved or runnable until real exact local Approval is issued.
