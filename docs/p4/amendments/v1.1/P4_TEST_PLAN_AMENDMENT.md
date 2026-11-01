# P4 acceptance amendment v1.1 — CR-P4-002

Owner-approved 2026-10-30; test-only correction. Immutable P4 v1.0 ZIP and P0/P1/P2/P3 remain unchanged.

**P4-T13:** read all **4 source data rows** and 6 columns of the frozen P0 P-B `input_orders.xlsx`, sheet `Orders`, in exact source order with cached values. Compare against the four-row P0 `input_preview.json` and all source bytes/SHA checks. Do not drop the duplicate source O-002 in the reader.

**P4-T42:** unchanged: approved seven-operation pipeline produces exactly **3 final transformed rows**, matching frozen P0 expected_result.csv.

All other test definitions and IDs remain unchanged. Runtime results and Gate B approval are separate.
