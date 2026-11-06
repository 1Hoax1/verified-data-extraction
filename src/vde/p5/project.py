"""Exact typed projection: only approved header metadata is normalized."""
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import unicodedata
from vde.execution.wire import decimal_text
from .errors import require


@dataclass(frozen=True)
class Projection:
    columns: tuple
    headers: tuple
    fields: tuple
    output: dict


def describe(brief, spec, columns):
    output = spec['output']
    names = tuple(output['column_order'])
    require(tuple(columns) == names and tuple(brief['output_contract']['column_order']) == names,
            'SCHEMA_MISMATCH', 'P4/Brief/Spec ordered columns differ')
    fields = {f['name']: f for f in spec['expected_schema']}
    brief_fields = {f['name']: f for f in brief['fields']}
    require(set(fields) == set(brief_fields) == set(names), 'SCHEMA_MISMATCH', 'Missing or extra approved field')
    headers = []
    for name in names:
        field, original = fields[name], brief_fields[name]
        header = unicodedata.normalize('NFC', field['output_name'].strip())
        require(header == field['output_name'] == original['output_name'],
                'SCHEMA_MISMATCH', 'Unprepared approved header metadata')
        require(all(field[k] == original[k] for k in ('data_type', 'required', 'nullable')),
                'SCHEMA_MISMATCH', 'Brief and Spec typed schema differ')
        headers.append(header)
    require(len(set(headers)) == len(headers), 'COLUMN_COLLISION', 'Colliding output headers')
    for key in ('format', 'file_name', 'sheet_name', 'encoding', 'delimiter'):
        require(output[key] == brief['output_contract'][key], 'SCHEMA_MISMATCH', 'Brief/Spec output differs')
    require(brief['output_contract']['include_header'] is True, 'SCHEMA_MISMATCH', 'Pilot requires a header')
    require(output['format'] in ('CSV', 'XLSX'), 'EXPORT_FAILED', 'Unsupported approved output format')
    require(output['file_name'].lower().endswith('.'+output['format'].lower()),
            'EXPORT_FAILED', 'Output filename extension differs')
    return Projection(names, tuple(headers), tuple(fields[n] for n in names), output)


def safe_csv_string(value):
    # Do not rewrite strings. CSV quoting does not disable spreadsheet formulas.
    position = 0
    while position < len(value) and (value[position].isspace() or ord(value[position]) < 32
                                     or 127 <= ord(value[position]) <= 159):
        position += 1
    significant = value[position:]
    require(not significant.startswith(('=', '+', '-', '@')), 'EXPORT_FAILED', 'Unsafe spreadsheet formula string in CSV')
    return value


def semantic_row(values, projection):
    """CR-P5-003: one exact, schema-directed widening; originals stay intact.

    The caller has already decoded/validated the original canonical P4 tags.
    Do not parse text or modify the original row, wire bytes or stored history.
    """
    require(len(values) == len(projection.fields), 'SCHEMA_MISMATCH', 'Semantic row shape differs')
    result = []
    for value, field in zip(values, projection.fields):
        if type(value) is int:
            require(-(2**63) <= value < 2**63, 'SCHEMA_MISMATCH', 'Integer outside signed64')
            if field['data_type'] == 'decimal':
                value = Decimal(value)
        result.append(value)
    return tuple(result)


def csv_cell(value):
    if value is None:
        return ''
    if type(value) is str:
        value.encode('utf-8', errors='strict')
        return safe_csv_string(value)
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is int:
        require(-(2**63) <= value < 2**63, 'EXPORT_FAILED', 'Integer outside signed64')
        return str(value)
    if type(value) is Decimal:
        text = decimal_text(value)
        return text if '.' in text else text+'.0'
    if type(value) in (date, datetime, time):
        return value.isoformat().replace('+00:00', 'Z')
    require(False, 'EXPORT_FAILED', 'Unsupported typed scalar')


def numeric_preflight(value):
    if type(value) is int:
        require(abs(value) <= 999999999999999, 'EXPORT_FAILED', 'XLSX integer exceeds conservative 15-digit bound')
    elif type(value) is Decimal:
        require(value.is_finite(), 'EXPORT_FAILED', 'Nonfinite Decimal')
        text = decimal_text(value).lstrip('-').replace('.', '').lstrip('0').rstrip('0')
        require(len(text) <= 15 and value.copy_abs() < Decimal('1000000000000000'),
                'EXPORT_FAILED', 'XLSX Decimal exceeds conservative exactness bound')
