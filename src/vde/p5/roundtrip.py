"""Independent full-table readback, including raw XML numeric lexemes."""
import csv
from decimal import Decimal, InvalidOperation
from itertools import zip_longest
from math import isfinite
import hashlib
from pathlib import PurePosixPath
import zipfile
from xml.etree import ElementTree as ET
from openpyxl import load_workbook
from .errors import P5Error, require
from .project import csv_cell

MISSING = object()
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def file_identity(path):
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def xml_rows(path):
    # P5 writes exactly one sheet. Resolve its actual workbook relationship;
    # never assume a package's sheet filename from a user-provided path.
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = workbook.find(NS+'sheets')
        require(len(sheets) == 1, 'ROUNDTRIP_MISMATCH', 'Unexpected worksheet count')
        rid = sheets[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        for relpath in archive.namelist():
            if relpath.endswith('.rels'):
                require(all(r.get('TargetMode') != 'External' for r in ET.fromstring(archive.read(relpath))),
                        'ROUNDTRIP_MISMATCH', 'External XLSX relationship forbidden')
        rel = next(r for r in rels if r.get('Id') == rid)
        target = rel.get('Target')
        require(rel.get('TargetMode') != 'External' and '..' not in PurePosixPath(target).parts,
                'ROUNDTRIP_MISMATCH', 'Unsafe worksheet relationship')
        name = target.lstrip('/') if target.startswith('/') else 'xl/'+target
        with archive.open(name) as stream:
            for event, node in ET.iterparse(stream, events=('end',)):
                if node.tag == NS+'row':
                    cells = {}
                    for cell in node:
                        value = cell.find(NS+'v')
                        kind = 'f' if cell.find(NS+'f') is not None else cell.get('t', 'n')
                        cells[cell.get('r')] = (kind, None if value is None else value.text)
                    yield cells
                    node.clear()
                elif node.tag == NS+'sheetData':
                    node.clear()


def numeric_equal(expected, value, cell_type, xml):
    require(type(value) in (int, float) and cell_type == 'n' and
            (type(value) is int or isfinite(value)), 'ROUNDTRIP_MISMATCH', 'Numeric XLSX cell has wrong type')
    require(xml is not None and xml[0] == 'n' and xml[1] is not None,
            'ROUNDTRIP_MISMATCH', 'Numeric OpenXML lexeme missing')
    require(Decimal(str(value)) == Decimal(expected) == Decimal(xml[1]),
            'ROUNDTRIP_MISMATCH', 'Numeric value changed in XML or openpyxl readback')


def verify(path, projection, rows, budget):
    count, cells = 0, 0
    size, checksum = file_identity(path)
    require(size > 0, 'ROUNDTRIP_MISMATCH', 'Empty export')
    try:
        if projection.output['format'] == 'CSV':
            previous = csv.field_size_limit(100000000)
            try:
                with path.open(encoding='utf-8', errors='strict', newline='') as stream:
                    reader = csv.reader(stream, delimiter=projection.output['delimiter'], strict=True)
                    require(next(reader, None) == list(projection.headers), 'ROUNDTRIP_MISMATCH', 'CSV header order differs')
                    for expected, actual in zip_longest(rows, reader, fillvalue=MISSING):
                        require(expected is not MISSING and actual is not MISSING and
                                [csv_cell(v) for v in expected] == actual,
                                'ROUNDTRIP_MISMATCH', 'CSV full lexical row differs')
                        count += 1
                        cells += len(expected)
                        if count % 100 == 0:
                            budget.check()
            finally:
                csv.field_size_limit(previous)
        else:
            binary = path.open('rb')
            try:
                workbook = load_workbook(binary, read_only=True, data_only=True, keep_links=False)
            except Exception:
                binary.close()
                raise
            try:
                require(workbook.sheetnames == [projection.output['sheet_name']],
                        'ROUNDTRIP_MISMATCH', 'XLSX sheet differs')
                reader, xml = iter(workbook.worksheets[0].rows), iter(xml_rows(path))
                header, header_xml = next(reader, None), next(xml, None)
                require(header is not None and tuple(c.value for c in header) == projection.headers and
                        all(c.data_type == 's' for c in header), 'ROUNDTRIP_MISMATCH', 'XLSX headers differ')
                for expected, actual, raw in zip_longest(rows, reader, xml, fillvalue=MISSING):
                    require(expected is not MISSING and actual is not MISSING and raw is not MISSING,
                            'ROUNDTRIP_MISMATCH', 'XLSX row count differs')
                    require(len(actual) == len(expected), 'ROUNDTRIP_MISMATCH', 'XLSX column count differs')
                    require(all(v[0] not in ('f', 'e') for v in raw.values()),
                            'ROUNDTRIP_MISMATCH', 'Formula or error present in worksheet XML')
                    for value, cell in zip(expected, actual):
                        require(cell.data_type not in ('f', 'e'), 'ROUNDTRIP_MISMATCH', 'Formula or error cell exported')
                        if type(value) in (int, Decimal):
                            numeric_equal(value, cell.value, cell.data_type, raw.get(cell.coordinate))
                        elif value is None:
                            require(cell.value is None, 'ROUNDTRIP_MISMATCH', 'Null cell changed')
                        elif type(value) is bool:
                            require(cell.data_type == 'b' and type(cell.value) is bool and cell.value == value,
                                    'ROUNDTRIP_MISMATCH', 'Boolean cell changed')
                        else:
                            target = value if type(value) is str else value.isoformat().replace('+00:00', 'Z')
                            # openpyxl exposes empty inline strings as None;
                            # require explicit inlineStr metadata for that case.
                            require((cell.value == target and cell.data_type == 's') or
                                    (target == '' and cell.value is None and cell.data_type == 'inlineStr'),
                                    'ROUNDTRIP_MISMATCH', 'Text or date cell changed')
                    count += 1
                    cells += len(expected)
                    if count % 100 == 0:
                        budget.check()
            finally:
                workbook.close()
                binary.close()
        require(file_identity(path) == (size, checksum), 'ROUNDTRIP_MISMATCH', 'Staged file changed during verification')
        budget.check()
        return dict(rows=count, columns=len(projection.columns), cells=cells,
                    headers=list(projection.headers), size=size, checksum=checksum,
                    formulas=0, errors=0, readable=True, exact=True)
    except P5Error:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, csv.Error, zipfile.BadZipFile,
            ET.ParseError, InvalidOperation, KeyError, StopIteration) as exc:
        raise P5Error('ROUNDTRIP_MISMATCH', 'Independent full-table readback failed') from exc
