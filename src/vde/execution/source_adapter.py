"""P4-owned full-row adapter, using the frozen P1 bytes/P2 parsing guards."""
import csv
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import io
import zipfile
import zlib
from xml.etree import ElementTree

from vde.ingestion.csv_reader import options, ENCODINGS
from vde.ingestion.diagnostics import IngestionError
from vde.ingestion.limits import CheckedBytesIO, raw_check
from vde.ingestion.preview import headers
from vde.ingestion.xlsx_reader import (archive, sheet_index, SelectedExcelReader, row_metadata, project)
from .errors import ExecutionError, require


@dataclass(frozen=True)
class Row:
    source: int
    values: tuple
    ordinal: int | None = None  # Ephemeral current-order witness for disk dedup.


@dataclass
class Source:
    columns: tuple
    rows: object
    warnings: list

    def close(self):
        close = getattr(self.rows, 'close', None)
        if close is not None:
            close()


def _csv(raw, selection, budget):
    options(**selection)
    previous = csv.field_size_limit(100000000)
    try:
        with io.TextIOWrapper(CheckedBytesIO(raw, budget), encoding=ENCODINGS[selection['encoding']],
                              errors='strict', newline='') as stream:
            reader = csv.reader(stream, delimiter=selection['delimiter'], strict=True)
            columns, count = None, 0
            for index, cells in enumerate(reader):
                if index % 1000 == 0:
                    budget.check()
                if index < selection['header_row']:
                    continue
                if columns is None:
                    headers(cells)
                    budget.shape(len(cells))
                    columns = tuple(cells)
                    yield columns
                else:
                    count += 1
                    budget.shape(len(columns), count)
                    require(len(cells) == len(columns), 'INPUT_UNREADABLE', 'RAGGED_ROW')
                    yield Row(count, tuple(cells))
            require(columns is not None, 'INPUT_UNREADABLE', 'MISSING_HEADER')
    finally:
        csv.field_size_limit(previous)


def _source_value(cell, metadata, epoch):
    value = project(cell, metadata, epoch)
    if isinstance(value, dict):
        require(value.get('kind') != 'excel_error', 'SCHEMA_MISMATCH', 'Excel error cell is not a scalar')
        kind = value['kind']
        return {'date': date.fromisoformat, 'datetime': datetime.fromisoformat,
                'time': time.fromisoformat}[kind](value['iso'])
    if metadata and metadata[4] == 'n' and metadata[3] is not None and type(value) in (int, float):
        # Use the actual stored XML number, never str(openpyxl's rounded float).
        text = metadata[3]
        if '.' in text or 'e' in text.lower():
            return Decimal(text)
        return int(text)
    return value


def _xlsx(raw, selected, budget, warnings, asset_id):
    book = None
    try:
        with archive(raw, budget) as z:
            index = dict(sheet_index(z))
            require(selected in index, 'INPUT_UNREADABLE', 'SHEET_NOT_FOUND')
            reader = SelectedExcelReader(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
            reader.selected_sheet, reader.selected_path = selected, index[selected]
            reader.archive.close()
            reader.archive, reader.valid_files = z, z.namelist()
            reader.read()
            book = reader.wb
            sheet = book[selected]
            sheet.reset_dimensions()
            values, expected_row, columns, formulas = iter(sheet.iter_rows()), 1, None, 0
            samples = []
            for number, metadata in row_metadata(z, index[selected]):
                require(columns is not None or number == 1, 'INPUT_UNREADABLE', 'PHYSICAL_ROW1_BLANK')
                while expected_row <= number:
                    cells = next(values)
                    current = metadata if expected_row == number else {}
                    projected = tuple(_source_value(c, current.get(i), book.epoch) for i, c in enumerate(cells, 1))
                    if expected_row == 1:
                        headers(list(projected))
                        budget.shape(len(projected))
                        columns = projected
                        yield columns
                    else:
                        budget.shape(len(columns), expected_row-1)
                        require(len(projected) <= len(columns), 'INPUT_UNREADABLE', 'RAGGED_ROW')
                        yield Row(expected_row-1, projected + (None,)*(len(columns)-len(projected)))
                    formulas += sum(bool(m[1]) for m in current.values())
                    for coordinate, formula, _, _, _ in current.values():
                        if formula and len(samples) < 20:
                            samples.append(coordinate)
                    if expected_row % 1000 == 0:
                        budget.check()
                    expected_row += 1
            require(next(values, None) is None and columns is not None, 'INPUT_UNREADABLE', 'WORKSHEET_STREAM_MISMATCH')
            if formulas:
                warnings.append({'code': 'XLSX_FORMULA_PRESENT', 'severity': 'WARNING', 'source_id': asset_id,
                                 'affected_count': formulas, 'sample_cells': samples})
    finally:
        if book is not None:
            book.close()


def _guard(iterator):
    try:
        yield from iterator
    except IngestionError as exc:
        if exc.reason in {'DATA_ROW_LIMIT', 'COLUMN_LIMIT'}:
            raise ExecutionError('SCHEMA_MISMATCH', 'P4_ROW_LIMIT' if exc.reason == 'DATA_ROW_LIMIT' else 'P4_COLUMN_LIMIT', stage='PREFLIGHT') from exc
        raise ExecutionError(exc.code, exc.reason) from exc
    except (UnicodeError, csv.Error, OSError, ValueError, KeyError, StopIteration, EOFError,
            AttributeError, IndexError, RuntimeError, OverflowError,
            ElementTree.ParseError, zipfile.BadZipFile, zlib.error) as exc:
        raise ExecutionError('INPUT_UNREADABLE', 'Malformed selected input') from exc
    finally:
        iterator.close()


def iter_verified_rows(env, plan, budget):
    asset = plan.asset
    raw = env.workspace.read_verified(asset.workspace_relpath, asset.byte_sha256, asset.size_bytes)
    raw_check(raw)
    budget.check()
    warnings, selection = [], plan.handoff.input_selection
    stream = _csv(raw, selection['csv_options'], budget) if selection['source_type'] == 'LOCAL_CSV' else _xlsx(raw, selection['sheet_name'], budget, warnings, asset.id)
    rows = _guard(stream)
    columns = next(rows)
    return Source(columns, rows, warnings)
