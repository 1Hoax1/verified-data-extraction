# Content Hash Specification

**Pack:** Pilot_Slice_V1_Contract_Pack_v1.0  
**Instance schema version:** `1.1`

## Algorithm

1. Build the exact semantic payload below.
2. Normalize every key and string value to Unicode NFC.
3. Serialize with RFC 8785 JSON Canonicalization Scheme.
4. Encode as UTF-8.
5. Compute SHA-256 and store lowercase hexadecimal digest.

Arrays are ordered. NaN/Infinity, duplicate keys, comments and non-JSON values are invalid.

## BriefVersion payload

Included exactly: `schema_version`, `objective`, `record_definition`, `scope`, `inputs_expected`, `output_contract`, `fields`, `volume_expectation`, `data_quality_expectations`, `acceptance_criteria`, `assumptions`, `open_questions`, `risks`.

Excluded: `version_id`, `order_id`, `version_number`, `created_at`, `source_refs`, `content_hash`, UI metadata and approval-derived values.

## TransformationSpecVersion payload

Included exactly: `schema_version`, `brief_version_id`, `brief_content_hash`, `inputs`, ordered `pipeline`, `output`, `execution_policy`, `provenance_policy`, `expected_schema`, `acceptance_criteria_ref`.

Excluded: `version_id`, `order_id`, `version_number`, `created_at`, `content_hash`, UI metadata and approval-derived values.

## Validation moments

Recalculate after loading, immediately before Approval, and immediately before Execute. Mismatch is `APPROVAL_HASH_MISMATCH` before input I/O.

Exact vectors are under `specifications/hash_vectors/`. Production code must use a conforming RFC 8785 implementation.


## 6. output_name normalization before hashing

Every stored field contains an explicit `output_name`. Before construction of the semantic
payload it is trimmed and normalized to Unicode NFC. The normalized value participates in
`fields` / `expected_schema` and therefore changes BriefVersion and TransformationSpecVersion
content hashes. `output_name` defaulting to `name` occurs before persistence and hashing.
