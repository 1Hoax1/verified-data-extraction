"""Bounded internal view; never a dataset, persisted selection or QA verdict."""
from dataclasses import dataclass, field
import json
from .diagnostics import require


@dataclass
class ReadResult:
    asset_id: str
    source_type: str
    selection: dict
    columns: list
    first_rows: list
    data_row_count: int
    byte_sha256: str
    formula_cell_count: int = 0
    formula_sample_addresses: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def column_count(self):
        return len(self.columns)


def bounded(columns, rows, warnings):
    for value in columns + [c for row in rows for c in row]:
        if isinstance(value, str):
            require(len(value) <= 65_536, 'PREVIEW_CELL_LIMIT')
    encoded = json.dumps({'columns': columns, 'first_rows': rows, 'warnings': warnings},
                         ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    require(len(encoded) <= 1_048_576, 'PREVIEW_JSON_LIMIT')


def headers(columns):
    require(bool(columns), 'PHYSICAL_ROW1_BLANK')
    require(len(columns) <= 200, 'COLUMN_LIMIT')
    require(all(isinstance(c, str) and c.strip() for c in columns), 'INVALID_HEADER')
    require(len(set(columns)) == len(columns), 'DUPLICATE_HEADER')
    bounded(columns, [], [])


def make_preview_document(result):
    summaries = []
    if result.formula_cell_count:
        summaries = [{'code': 'XLSX_FORMULA_PRESENT', 'severity': 'WARNING',
                      'affected_count': result.formula_cell_count,
                      'sample_cells': result.formula_sample_addresses}]
    bounded(result.columns, result.first_rows, summaries)
    return {'schema_version': '1.1', 'asset_id': result.asset_id,
            'source_type': result.source_type, **result.selection,
            'columns': result.columns, 'first_rows': result.first_rows, 'warnings': summaries}
