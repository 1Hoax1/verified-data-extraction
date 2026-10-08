"""Read-only access to the approved P0 pack; no ingestion or execution."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
import rfc8785

PACK = Path(__file__).resolve().parents[2] / "pecs/pilot_slice_v1"
BRIEF_FIELDS = (
    "schema_version objective record_definition scope inputs_expected output_contract "
    "fields volume_expectation data_quality_expectations acceptance_criteria "
    "assumptions open_questions risks"
).split()
SPEC_FIELDS = (
    "schema_version brief_version_id brief_content_hash inputs pipeline output "
    "execution_policy provenance_policy expected_schema acceptance_criteria_ref"
).split()


def loads(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-JSON numeric constant")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def dumps(document):
    return json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


@lru_cache
def validators():
    schemas = {p.name: loads(p.read_text(encoding="utf-8")) for p in (PACK / "contracts").rglob("*.schema.json")}
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas.values())
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    return {name: Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()) for name, schema in schemas.items()}


def validate(document, schema):
    validators()[schema + ".schema.json"].validate(document)


def nfc(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [nfc(v) for v in value]
    if isinstance(value, dict):
        result = {}
        for key, val in value.items():
            normalized = nfc(key)
            if normalized in result:
                raise ValueError("Duplicate NFC key")
            result[normalized] = nfc(val)
        return result
    return value


def hash_payload(payload):
    return hashlib.sha256(rfc8785.dumps(nfc(payload))).hexdigest()


def content_hash(document, kind):
    fields = BRIEF_FIELDS if kind == "brief_version" else SPEC_FIELDS
    # output_name is already explicit in persisted P0 contracts. Reject unprepared
    # names instead of silently modifying the authoritative document.
    for field in document["fields" if kind == "brief_version" else "expected_schema"]:
        name = field["output_name"]
        if name != unicodedata.normalize("NFC", name.strip()):
            raise ValueError("Unnormalized output_name")
    return hash_payload({key: document[key] for key in fields})
