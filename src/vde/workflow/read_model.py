"""Ephemeral review DTOs, and deterministic before/after JSON paths."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VerifiedSelection:
    order_id: str
    asset_id: str
    byte_sha256: str
    source_type: str
    selection: dict
    columns: list
    first_rows: list
    warnings: list = field(default_factory=list)


@dataclass(frozen=True)
class VersionReview:
    version_id: str
    content_hash: str
    document: dict
    selected: bool
    approval_id: str | None
    diff: list


@dataclass(frozen=True)
class ApprovalView:
    order: Any
    brief: VersionReview | None
    spec: VersionReview | None


@dataclass(frozen=True)
class P4Handoff:
    order_id: str
    brief_version_id: str
    brief_content_hash: str
    brief_approval_id: str
    transformation_spec_version_id: str
    transformation_content_hash: str
    transformation_approval_id: str
    asset_id: str
    byte_sha256: str
    input_selection: dict


def json_diff(before, after, path=''):
    """Stable JSON Pointer order; preserve array order and distinguish missing/null."""
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            pointer = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in before:
                result.append({'path': pointer, 'change': 'add', 'after': after[key]})
            elif key not in after:
                result.append({'path': pointer, 'change': 'remove', 'before': before[key]})
            else:
                result.extend(json_diff(before[key], after[key], pointer))
        return result
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [item for i, (left, right) in enumerate(zip(before, after))
                for item in json_diff(left, right, path + '/' + str(i))]
    return [] if type(before) is type(after) and before == after else [
        {'path': path, 'change': 'replace', 'before': before, 'after': after}]
