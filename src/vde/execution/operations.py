"""Pure closed-operation semantics: immutable rows, no I/O, clocks or callbacks."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from jsonschema.exceptions import ValidationError
from vde.contracts import validate
from vde.workflow.validation import OPERATIONS
from .errors import ExecutionError, require
from .source_adapter import Row

FORMATS = {'YYYY-MM-DD': ('%Y-%m-%d', r'\d{4}-\d{2}-\d{2}'),
           'DD.MM.YYYY': ('%d.%m.%Y', r'\d{2}\.\d{2}\.\d{4}'),
           'DD/MM/YYYY': ('%d/%m/%Y', r'\d{2}/\d{2}/\d{4}'),
           'MM/DD/YYYY': ('%m/%d/%Y', r'\d{2}/\d{2}/\d{4}'),
           'YYYY/MM/DD': ('%Y/%m/%d', r'\d{4}/\d{2}/\d{2}'),
           'YYYY-MM-DD HH:mm:ss': ('%Y-%m-%d %H:%M:%S', r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'),
           'DD.MM.YYYY HH:mm:ss': ('%d.%m.%Y %H:%M:%S', r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}')}


def missing(value):
    return value is None or type(value) is str and value == ''


def plan_columns(columns, op):
    require(op.get('type') in OPERATIONS, 'INVALID_OPERATION', 'Outside the 12-operation whitelist', operation=op)
    try:
        validate(op, op['type'])
    except ValidationError as exc:
        raise ExecutionError('INVALID_PARAMETER', 'Invalid closed operation parameters', operation=op) from exc
    p, kind = op['params'], op['type']
    keys = p.get('columns', p.get('subset', p.get('by', [p['column']] if 'column' in p else [])))
    if kind == 'rename':
        keys = list(p['mapping'])
    if kind != 'drop_columns' or not p['ignore_missing']:
        require(set(keys) <= set(columns), 'COLUMN_NOT_FOUND', 'Required column absent', operation=op,
                column=next((k for k in keys if k not in columns), None), stage='PREFLIGHT')
    if kind == 'sort':
        require(len(p['by']) == len(p['ascending']), 'INVALID_PARAMETER', 'Sort direction count mismatch', operation=op)
    if kind == 'select_columns':
        output = tuple(p['columns'])
    elif kind == 'drop_columns':
        output = tuple(c for c in columns if c not in p['columns'])
    elif kind == 'rename':
        output = tuple(p['mapping'].get(c, c) for c in columns)
        require(len(set(output)) == len(output), 'COLUMN_COLLISION', 'Rename output collision', operation=op)
    else:
        output = tuple(columns)
    require(bool(output), 'SCHEMA_MISMATCH', 'Zero-column result forbidden', operation=op)
    return output


def parse_number(value, p):
    if missing(value):
        return None
    require(type(value) in (str, int, Decimal), 'PARSE_FAILED', 'P4_PARSE_FAILED')
    if type(value) is str:
        decimal, group = p['decimal_separator'], p['thousands_separator']
        digits = r'[0-9]+'
        if group is not None:
            digits = '(?:[0-9]+|[0-9]{1,3}(?:' + re.escape(group) + '[0-9]{3})+)'
        fraction = '(?:' + re.escape(decimal) + '[0-9]+)?' if p['target_type'] == 'decimal' else ''
        require(re.fullmatch('[+-]?' + digits + fraction, value, re.ASCII) is not None,
                'PARSE_FAILED', 'P4_PARSE_FAILED')
        text = value.replace(group, '') if group is not None else value
        number = Decimal(text.replace(decimal, '.'))
    else:
        number = Decimal(value)
    require(number.is_finite(), 'PARSE_FAILED', 'P4_PARSE_FAILED')
    if p['target_type'] == 'integer':
        require(number == number.to_integral_value() and -(2**63) <= number <= 2**63-1,
                'PARSE_FAILED', 'P4_PARSE_FAILED')
        return int(number)
    return number


def parse_date(value, p):
    if missing(value):
        return None
    parsed = value if type(value) in (date, datetime) else None
    if parsed is None and type(value) is str:
        for token in p['formats']:
            fmt, pattern = FORMATS[token]
            if re.fullmatch(pattern, value, re.ASCII):
                try:
                    parsed = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    pass
    require(parsed is not None, 'PARSE_FAILED', 'P4_PARSE_FAILED')
    if p['output_format'] == 'YYYY-MM-DD':
        return parsed.date() if type(parsed) is datetime else parsed
    require(type(parsed) is datetime and parsed.tzinfo is not None
            and parsed.utcoffset().total_seconds() == 0, 'PARSE_FAILED', 'P4_PARSE_FAILED')
    return parsed.astimezone(timezone.utc)


def apply_one(columns, row, op, audit):
    """Apply one nonblocking operation to a row; None means an approved deletion."""
    kind, p = op['type'], op['params']
    if kind == 'rename':
        return row
    if kind in {'select_columns', 'drop_columns'}:
        output = p['columns'] if kind == 'select_columns' else [c for c in columns if c not in p['columns']]
        return Row(row.source, tuple(row.values[columns.index(c)] for c in output), row.ordinal)
    if kind == 'drop_missing':
        flags = [missing(row.values[columns.index(c)]) for c in p['subset']]
        if (any(flags) if p['how'] == 'any' else all(flags)):
            if len(audit['deleted_row_sample']) < 20:
                audit['deleted_row_sample'].append(row.source)
            return None
        return row
    values = list(row.values)
    selected = p.get('columns', [p['column']] if 'column' in p else [])
    for column in selected:
        index, value = columns.index(column), row.values[columns.index(column)]
        try:
            if kind == 'trim':
                if type(value) is str:
                    values[index] = {'both': str.strip, 'left': str.lstrip, 'right': str.rstrip}[p['mode']](value)
            elif kind == 'change_case':
                require(value is None or type(value) is str, 'SCHEMA_MISMATCH', 'Case operand must be a string')
                if value is not None:
                    values[index] = {'lower': str.lower, 'upper': str.upper, 'title': str.title}[p['mode']](value)
            elif kind == 'replace':
                require(value is None or type(value) is str, 'SCHEMA_MISMATCH', 'Replace operand must be a string')
                if value is not None:
                    values[index] = p['mapping'].get(value, value) if 'mapping' in p else p['new'] if value == p['old'] else value
            elif kind == 'fill_missing':
                if missing(value):
                    values[index] = p['value']
            elif kind in {'parse_number', 'parse_date'}:
                values[index] = (parse_number if kind == 'parse_number' else parse_date)(value, p)
        except (ExecutionError, ValueError, InvalidOperation, OverflowError) as exc:
            code = exc.code if isinstance(exc, ExecutionError) else 'PARSE_FAILED'
            if kind in {'parse_number', 'parse_date'} and p['errors'] == 'SET_NULL' and code == 'PARSE_FAILED':
                values[index] = None
                audit['parse_failed_count'] += 1
                if len(audit['parse_failed_sample']) < 20:
                    audit['parse_failed_sample'].append({'row_id': row.source, 'value': str(value)[:500]})
            else:
                raise ExecutionError(code, str(exc), operation=op, column=column,
                                     row_id=row.source, value=value) from exc
    return Row(row.source, tuple(values), row.ordinal)
