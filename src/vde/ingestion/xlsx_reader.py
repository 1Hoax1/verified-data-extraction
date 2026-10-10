"""ZIP preflight, guarded OOXML streams and cached-only read-only openpyxl."""
import hashlib
import io
import math
import posixpath
import stat
import zipfile
from datetime import date, datetime, time
from xml.etree import ElementTree as ET

from openpyxl.reader.excel import ExcelReader
from openpyxl.styles.numbers import is_datetime
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries
from openpyxl.cell.cell import ERROR_CODES

from .diagnostics import IngestionError, diagnostic, require
from .limits import Budget, CHUNK, COLS, ROWS, raw_check
from .preview import ReadResult, bounded, headers, make_preview_document

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


class GuardedStream:
    """Never request more than one MiB from an inflater; check every chunk."""
    def __init__(self, stream, info, archive):
        self.stream, self.info, self.archive = stream, info, archive
        self.count = 0
        self.tail = b''

    def read(self, size=-1):
        # XML and openpyxl can request read(-1). Service it in checked chunks.
        if size < 0 or size > CHUNK:
            parts = []
            remaining = size
            while remaining != 0:
                part = self.read(CHUNK if remaining < 0 else min(CHUNK, remaining))
                if not part:
                    break
                parts.append(part)
                if remaining > 0:
                    remaining -= len(part)
            return b''.join(parts)
        data = self.stream.read(size)
        self.count += len(data)
        require(self.count <= self.info.file_size and self.count <= 100_000_000,
                'ZIP_ACTUAL_MEMBER_LIMIT')
        self.archive.observed[self.info.filename] = max(self.count, self.archive.observed.get(self.info.filename, 0))
        require(sum(self.archive.observed.values()) <= 250_000_000, 'ZIP_ACTUAL_TOTAL_LIMIT')
        if self.info.filename.lower().endswith(('.xml', '.rels')):
            # Removing NUL covers UTF-16/32 markup too; tail covers split tokens.
            scan = (self.tail + data.replace(b'\x00', b'')).upper()
            require(b'<!DOCTYPE' not in scan and b'<!ENTITY' not in scan, 'UNSAFE_XML_DECLARATION')
            self.tail = scan[-32:]
        self.archive.budget.check()
        if not data and size:
            require(self.count == self.info.file_size, 'ZIP_ACTUAL_SIZE_MISMATCH')
        return data

    def close(self):
        self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SafeZip(zipfile.ZipFile):
    def __init__(self, raw, budget):
        super().__init__(io.BytesIO(raw))
        self.budget, self.observed = budget, {}
        entries = self.infolist()
        require(len(entries) <= 10_000, 'ZIP_ENTRY_COUNT_LIMIT')
        seen = set()
        for member in entries:
            name = member.filename
            norm = posixpath.normpath(name)
            mode = member.external_attr >> 16
            require(name and not name.startswith('/') and '\\' not in name and ':' not in name
                    and '..' not in name.split('/') and norm not in seen, 'ZIP_UNSAFE_PATH')
            seen.add(norm)
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'ZIP_SPECIAL_FILE')
            require(not member.flag_bits & 1, 'ZIP_ENCRYPTED')
            require(member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'ZIP_COMPRESSION')
            require(0 <= member.file_size <= 100_000_000, 'ZIP_MEMBER_LIMIT')
            require(member.compress_size >= 0 and member.header_offset >= 0, 'ZIP_INVALID_METADATA')
            if norm == 'xl/sharedStrings.xml':
                require(member.file_size <= 16_000_000, 'ZIP_SHARED_STRINGS_LIMIT')
        require(sum(m.file_size for m in entries) <= 250_000_000, 'ZIP_TOTAL_EXPANDED_LIMIT')
        for member in entries:
            require(not member.file_size or (member.compress_size > 0 and
                    member.file_size <= 100 * member.compress_size), 'ZIP_RATIO_LIMIT')
        budget.check()

    def open(self, name, mode='r', pwd=None, *, force_zip64=False):
        require(mode == 'r', 'ZIP_READ_ONLY')
        info = name if isinstance(name, zipfile.ZipInfo) else self.getinfo(name)
        return GuardedStream(super().open(info, mode, pwd), info, self)

    def read(self, name, pwd=None):
        # openpyxl reads small workbook/style parts this way. The checked stream
        # chunks inflation and samples RSS, including when read(-1) is requested.
        with self.open(name, pwd=pwd) as stream:
            return stream.read()


def archive(raw, budget):
    raw_check(raw)
    try:
        return SafeZip(raw, budget)
    except IngestionError:
        raise
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise IngestionError('INVALID_ZIP') from exc


def xml_elements(z, name):
    """Streaming events with bounded detached row/metadata elements."""
    with z.open(name) as stream:
        stack = []
        for event, elem in ET.iterparse(stream, events=('start', 'end')):
            if event == 'start':
                stack.append(elem)
            else:
                yield elem
                # Preserve children only inside a row. No all-row root retention.
                if elem.tag == NS + 'row' or not any(e.tag == NS + 'row' for e in stack):
                    if len(stack) > 1:
                        stack[-2].remove(elem)
                    elem.clear()
                stack.pop()


def sheet_index(z):
    relations = {}
    for elem in xml_elements(z, 'xl/_rels/workbook.xml.rels'):
        if elem.tag.endswith('}Relationship'):
            identity, target = elem.get('Id'), elem.get('Target', '')
            # External relationships are never dereferenced or downloaded.
            if elem.get('Type', '').endswith('/worksheet'):
                require(elem.get('TargetMode') != 'External', 'EXTERNAL_WORKSHEET')
                path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
                require(path in z.namelist() and path.startswith('xl/'), 'INVALID_SHEET_TARGET')
                require(identity not in relations, 'DUPLICATE_SHEET_RELATIONSHIP')
                relations[identity] = path
    sheets = []
    for elem in xml_elements(z, 'xl/workbook.xml'):
        if elem.tag == NS + 'sheet':
            name = elem.get('name')
            require(isinstance(name, str) and name and len(name) <= 128 and
                    name not in [s[0] for s in sheets], 'INVALID_SHEET_INDEX')
            require(elem.get(REL) in relations, 'INVALID_SHEET_RELATIONSHIP')
            sheets.append((name, relations[elem.get(REL)]))
    require(bool(sheets), 'EMPTY_WORKBOOK')
    return sheets


def list_sheets(raw, *, budget=None):
    budget = budget or Budget()
    try:
        with archive(raw, budget) as z:
            return [name for name, _ in sheet_index(z)]
    except IngestionError:
        raise
    except (ET.ParseError, KeyError, ValueError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise IngestionError('INVALID_WORKBOOK_XML') from exc


def row_metadata(z, path):
    """Yield each physical XML row; inspect merges through EOF too."""
    previous = 0
    for elem in xml_elements(z, path):
        if elem.tag == NS + 'mergeCell':
            _, min_row, _, max_row = range_boundaries(elem.get('ref'))
            require(not min_row <= 1 <= max_row, 'MERGED_HEADER')
        if elem.tag != NS + 'row':
            continue
        number = int(elem.get('r', '0'))
        require(number > previous, 'INVALID_ROW_ORDER')
        require(number <= ROWS + 1, 'DATA_ROW_LIMIT')
        previous = number
        cells, last_col = {}, 0
        for cell in elem:
            require(cell.tag == NS + 'c', 'INVALID_ROW_CELL')
            coordinate = cell.get('r', '')
            cell_row, col = coordinate_to_tuple(coordinate)
            require(cell_row == number and col > last_col, 'INVALID_CELL_ORDER')
            require(col <= COLS, 'COLUMN_LIMIT')
            last_col = col
            typ = cell.get('t', 'n')
            require(typ in ('n', 'b', 'e', 's', 'str', 'inlineStr', 'd'), 'UNKNOWN_CELL_TYPE')
            value, formula = cell.find(NS + 'v'), cell.find(NS + 'f')
            text = None if value is None else value.text
            empty = False
            if formula is not None:
                require(value is not None and (typ == 'str' or text not in (None, '')),
                        'SELECTED_FORMULA_CACHE_ABSENT', 'XLSX_FORMULA_CACHE_MISSING')
                require(typ in ('n', 'b', 'e', 's', 'str'), 'INVALID_FORMULA_CACHE_TYPE')
                empty = typ == 'str' and text is None
            if text not in (None, ''):
                if typ == 'b':
                    require(text in ('0', '1'), 'INVALID_BOOLEAN_CACHE')
                elif typ == 'e':
                    require(text in ERROR_CODES, 'INVALID_EXCEL_ERROR')
                elif typ == 's':
                    require(text.isdecimal(), 'INVALID_SHARED_STRING_INDEX')
                elif typ == 'n':
                    require(math.isfinite(float(text)), 'NONFINITE_NUMBER')
            cells[col] = (coordinate, formula is not None, empty, text, typ)
        yield number, cells


def project(cell, meta, epoch):
    if meta and meta[2]:
        return ''
    value = cell.value
    if cell.data_type == 'e':
        require(value in ERROR_CODES, 'INVALID_EXCEL_ERROR')
        return {'kind': 'excel_error', 'value': value}
    if getattr(cell, 'is_date', False) and meta and meta[3] is not None and meta[4] == 'n':
        require(not (epoch.year == 1899 and 60 <= float(meta[3]) < 61), 'EXCEL_LEAP_DATE_ANOMALY')
    if isinstance(value, datetime):
        if is_datetime(cell.number_format) == 'date':
            return {'kind': 'date', 'iso': value.date().isoformat()}
        return {'kind': 'datetime', 'iso': value.isoformat()}
    if isinstance(value, time):
        return {'kind': 'time', 'iso': value.isoformat()}
    if isinstance(value, date):
        return {'kind': 'date', 'iso': value.isoformat()}
    require(value is None or type(value) in (str, int, float, bool), 'UNREPRESENTABLE_CELL')
    if type(value) is float:
        require(math.isfinite(value), 'NONFINITE_NUMBER')
    return value


def read_xlsx(raw, *, asset_id, sheet_name, byte_sha256=None, budget=None):
    require(isinstance(sheet_name, str) and sheet_name, 'SHEET_REQUIRED')
    budget = budget or Budget()
    workbook = None
    try:
        with archive(raw, budget) as z:
            index = dict(sheet_index(z))
            require(sheet_name in index, 'SHEET_NOT_FOUND')
            # ExcelReader construction only opens its ZIP directory. Replace the
            # archive before read() so ALL library decompression uses our guards.
            reader = ExcelReader(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
            reader.archive.close()
            reader.archive = z
            reader.valid_files = z.namelist()
            reader.read()
            workbook = reader.wb
            sheet = workbook[sheet_name]
            sheet.reset_dimensions()  # Ignore stale dimension metadata; scan EOF.
            values = iter(sheet.iter_rows())
            expected_row, columns, rows, formulas, samples = 1, None, [], 0, []
            count = 0
            for number, metadata in row_metadata(z, index[sheet_name]):
                require(number != 1 or metadata, 'PHYSICAL_ROW1_BLANK')
                require(columns is not None or number == 1, 'PHYSICAL_ROW1_BLANK')
                # openpyxl supplies absent physical data rows as blank rows.
                while expected_row <= number:
                    row = next(values)
                    current_meta = metadata if expected_row == number else {}
                    require(len(row) <= COLS, 'COLUMN_LIMIT')
                    projected = [project(c, current_meta.get(i), workbook.epoch) for i, c in enumerate(row, 1)]
                    if expected_row == 1:
                        headers(projected)
                        columns = projected
                    else:
                        count += 1
                        require(count <= ROWS, 'DATA_ROW_LIMIT')
                        require(len(projected) <= len(columns), 'RAGGED_ROW')
                        projected += [None] * (len(columns) - len(projected))
                        if count <= 5:
                            bounded(columns, rows + [projected], [])
                            rows.append(projected)
                    for coordinate, formula, _, _, _ in current_meta.values():
                        if formula:
                            formulas += 1
                            if len(samples) < 20:
                                samples.append(coordinate)
                    if expected_row % 1000 == 0:
                        budget.check()
                    expected_row += 1
            # Exhaust both streams: malformed XML/footer and merged header are fatal.
            require(next(values, None) is None, 'WORKSHEET_STREAM_MISMATCH')
            require(columns is not None, 'PHYSICAL_ROW1_BLANK')
            warnings = [diagnostic('XLSX_FORMULA_PRESENT', f'{formulas} selected formula cells; cached values only.',
                                   source_id=asset_id)] if formulas else []
            result = ReadResult(asset_id, 'LOCAL_XLSX', {'selected_sheet': sheet_name}, columns, rows,
                                count, byte_sha256 or hashlib.sha256(raw).hexdigest(), formulas, samples, warnings)
            make_preview_document(result)
            budget.check()
            return result
    except IngestionError:
        raise
    except (ET.ParseError, KeyError, ValueError, TypeError, IndexError, OSError,
            zipfile.BadZipFile, RuntimeError, StopIteration, OverflowError) as exc:
        raise IngestionError('INVALID_XLSX_CONTENT') from exc
    finally:
        if workbook is not None:
            workbook.close()
