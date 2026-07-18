# Exact Changes from the Previous Archive

1. CSV input encoding enum expanded from UTF-8/UTF-8-SIG to UTF-8/UTF-8-SIG/CP1251; delimiter remains explicit comma/semicolon/tab; preview and INPUT_UNREADABLE policy formalized.
2. parse_date now schema-rejects a formats list containing both DD/MM/YYYY and MM/DD/YYYY; automatic date-order guessing is explicitly forbidden.
3. Added XLSX_FORMULA_PRESENT and XLSX_FORMULA_CACHE_MISSING to the error registry and execution error contract; formula cached-value policy added.
4. Added required stored output_name to every BriefVersion.fields and TransformationSpecVersion.expected_schema field; actual export headers are Unicode while internal names remain ASCII technical identifiers.
5. QAReport.dataset_summary now carries both internal columns and actual output_headers.
6. P-A changed to an actual CP1251 CSV with Cyrillic data and Unicode exported headers.
7. P-B now contains formula cells with cached values; expected XLSX export is values-only and QA status is PASS_WITH_WARNINGS.
8. All four fixtures, semantic payloads, approvals, content hashes, expected artifacts and QA reports were regenerated.
9. Traceability Matrix, validation rules, validation report and package manifest were updated.
