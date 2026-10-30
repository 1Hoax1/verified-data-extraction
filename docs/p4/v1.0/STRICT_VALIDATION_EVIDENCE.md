# P4 v0.4.1 — strict checkout validation (preserved evidence summary)

**Evidence date:** 2026-10-30.  
**Source:** Codex-generated `P4_v0.4.1_STRICT_VALIDATION.md` supplied by the owner; its complete text is also embedded byte-for-byte in the approved ZIP.  
**Checkout:** `411fda98b499646b355782d3ca3c34e20f9322ae`; CWD `/workspace/verified-data-extraction`; real root `pecs/pilot_slice_v1`.  
**Candidate archive:** `P4_Implementation_Pack_v0.4.1_candidate.zip` (79f725fd96075f3ca87b6172819d82b557f5e373b1f5ebc46f08cfbe8b2e3d0a, 104894 bytes).  
**Interpreter:** Python 3.12.14 / jsonschema 4.26.0 / referencing 0.37.0 / rfc8785 0.1.4.

## Actual executed command (as recorded by Codex)

```bash
REPO="$(git rev-parse --show-toplevel)"
python /tmp/p4-v0.4.1-strict-cgv_kz4f/P4_Implementation_Pack_v0.4.1_candidate/tools/verify_p4_fixture_consistency.py \
  --p0-root "$REPO/pecs/pilot_slice_v1" --require-p0 --mutation-probes
```

- **Exit code: 0**; stderr **0 bytes**.
- Main stdout result `STATIC_PINS_REFS_AND_P0_CONTRACTS_PASS`, `P0_checkout=CHECKED`.
- 38 operation cases; 19 failure cases, all 19 postconditions exact; 2 goldens; **36** P0-schema-valid operations; **2** intentionally schema-invalid rejected; **1** semantic-invalid identified.
- 45 precision W cases (13 signed64 roundtrips, 26 bad wire rejections, 2 Unicode exact oracles, 4 source integer overflows).
- **9/9** isolated mutation probes rejected (each intentionally exits 1; main strict command exits 0): primary_link, expected_cell, p0_golden_country, noncanonical_decimal, x17_stale_run, integer_rounded_through_binary64, bare_json_integer, invalid_tag_now_accepted, global_nfc.
- Genuine P0 operation union, all 12 operation schemas, two approved golden CSV, and two Spec JSONs checked against their exact commit and P0 manifest; file hashes also independently checked by the reviewer.
- `operation_semantic_execution=NOT_RUN`, `runtime_gate_b=NOT_RUN` — static/contract validation is not runtime acceptance.

The reviewer independently verified candidate/approved ZIP hashes and source byte identity and reran local static verification but **did not re-run strict P0 verifier on a separate repository checkout**. Original complete Codex report is retained inside the approved archive; this GitHub Markdown summary is not falsified stdout.
