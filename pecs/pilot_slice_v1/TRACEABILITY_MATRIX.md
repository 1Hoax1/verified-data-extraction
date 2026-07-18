# Traceability Matrix

| ID | Requirement | Contract | Fixture | Expected verification |
|---|---|---|---|---|
| TR-001 | One local CSV or one selected XLSX sheet | brief/spec schemas | P-A; P-B | schema + DQ-001 |
| TR-002 | No JSON/URL/API/HTML | source_type enums | All | unsupported source types fail |
| TR-003 | Manual versioned Brief | brief schema | All | valid briefs |
| TR-004 | Manual versioned TransformationSpec | spec schema | All | valid specs |
| TR-005 | Exactly 12 Pilot operations | operation union | All | filter rejected |
| TR-006 | No arbitrary code/expression/regex | schemas; replace regex=false | P-A; P-D | script/regex examples fail |
| TR-007 | Approval sole truth | approval schema/rules | P-C | mutations derive unapproved |
| TR-008 | No approval fields in versions | brief/spec schemas | P-A; P-C | extra properties fail |
| TR-009 | Two compatible approvals for APPROVED | approval/state rules | P-C | PC-1..PC-5 |
| TR-010 | NFC + RFC8785 + SHA-256 | content hash spec | P-C; vectors | exact hashes |
| TR-011 | Deterministic execution only | operation schemas | P-A; P-B | declared operations only |
| TR-012 | CSV UTF-8/XLSX export | output contracts | P-A; P-B | DQ-006/007 |
| TR-013 | Round-trip validation | QA contracts | P-A; P-B | DQ-022 |
| TR-014 | Input checksum | hash spec/QA | All | DQ-002 |
| TR-015 | Required columns/values | criterion/QA | P-A; P-D | DQ-008/012 |
| TR-016 | Duplicates | criterion/QA | P-A; P-B; P-D | DQ-014 |
| TR-017 | Parse FAIL/SET_NULL | parse schemas/policies | P-A; P-B; P-D | DQ-015/016; PARSE_FAILED |
| TR-018 | Deletion audited | drop/deduplicate | P-A; P-B | DQ-025 |
| TR-019 | No LLM | QA report const NOT_APPLICABLE | All | LLM status fixed |
| TR-020 | 10 states/3 stages | registries/rules | P-C | state cases |
| TR-021 | Structured errors | error schema/codes | P-D | exact codes |
| TR-022 | Closed objects/enums | all contracts | All | invalid examples fail |

| TR-023 | CSV encoding/delimiter explicitly selected; no detection/fallback; decode/parse error INPUT_UNREADABLE | transformation_spec_version.schema.json; pilot_ingestion_rules.md; pilot_error_policies.md | P-A | CP1251 preview succeeds; AUTO encoding example fails; wrong decode maps to INPUT_UNREADABLE |
| TR-024 | DD/MM/YYYY and MM/DD/YYYY cannot coexist in one parse_date operation | parse_date.schema.json; pilot_ingestion_rules.md | P-A; P-B | ambiguous x-invalid example is schema-rejected |
| TR-025 | XLSX formulas use cached values only; warning/error codes fixed; exports contain values only | error_codes.json; execution_error.schema.json; pilot_ingestion_rules.md | P-B | source has 4 cached formulas, warning emitted; output has zero formulas; missing-cache case maps to XLSX_FORMULA_CACHE_MISSING |
| TR-026 | Internal ASCII name separated from Unicode actual output_name | brief_version.schema.json; transformation_spec_version.schema.json; qa_report.schema.json | P-A; P-B; P-C; P-D | output_name schema/semantic checks, Unicode artifact headers and invalid tab-header cases |
