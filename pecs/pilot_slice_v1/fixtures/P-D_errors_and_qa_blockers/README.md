# P-D — Errors and QA Blockers

The approved SET_NULL pipeline produces `expected_result.csv`, then deterministic QA returns FAIL and order state NEEDS_FIX due to required nulls, duplicate id and type failures. Separate semantic cases define COLUMN_NOT_FOUND, COLUMN_COLLISION and PARSE_FAILED.
