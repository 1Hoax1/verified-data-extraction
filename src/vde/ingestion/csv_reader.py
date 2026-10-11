"""Strict explicit CSV decoding and complete bounded logical-record scan."""
import csv
import hashlib
import io
from .diagnostics import IngestionError, require
from .limits import Budget, ROWS, raw_check, CheckedBytesIO
from .preview import ReadResult, bounded, headers, make_preview_document

ENCODINGS = {'UTF-8': 'utf-8', 'UTF-8-SIG': 'utf-8-sig', 'CP1251': 'cp1251'}
DELIMITERS = {',': 'comma', ';': 'semicolon', '\t': 'tab'}


def options(encoding, delimiter, header_row):
    require(isinstance(encoding, str) and encoding in ENCODINGS, 'INVALID_ENCODING')
    require(isinstance(delimiter, str) and delimiter in DELIMITERS, 'INVALID_DELIMITER')
    require(type(header_row) is int and 0 <= header_row <= 100, 'INVALID_HEADER_ROW')


def read_csv(raw, *, asset_id, encoding, delimiter, header_row, byte_sha256=None, budget=None):
    options(encoding, delimiter, header_row)
    budget = budget or Budget()
    raw_check(raw)
    budget.check()
    # csv's process-global field cap is restored even on parser failure. P2 is
    # single-user/process; cap one parser field at the maximum raw payload size.
    previous = csv.field_size_limit(100_000_000)
    rows, count, columns = [], 0, None
    try:
        with io.TextIOWrapper(CheckedBytesIO(raw, budget), encoding=ENCODINGS[encoding], errors='strict', newline='') as text:
            reader = csv.reader(text, delimiter=delimiter, strict=True)
            for index, row in enumerate(reader):
                # Sample even while skipping explicitly selected pre-header records.
                if index % 1000 == 0:
                    budget.check()
                if index < header_row:
                    continue
                if columns is None:
                    headers(row)
                    columns = row
                    continue
                count += 1
                require(count <= ROWS, 'DATA_ROW_LIMIT')
                require(len(row) == len(columns), 'RAGGED_ROW')
                if count <= 5:
                    bounded(columns, rows + [row], [])
                    rows.append(row)
            require(columns is not None, 'MISSING_HEADER')
    except (UnicodeError, csv.Error, OSError) as exc:
        raise IngestionError('CSV_DECODE_OR_PARSE_FAILED') from exc
    finally:
        csv.field_size_limit(previous)
    budget.check()
    result = ReadResult(asset_id, 'LOCAL_CSV',
                        {'selected_encoding': encoding, 'selected_delimiter': DELIMITERS[delimiter]},
                        columns, rows, count, byte_sha256 or hashlib.sha256(raw).hexdigest())
    make_preview_document(result)
    return result
