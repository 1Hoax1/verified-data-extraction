"""Exact P4_INTERNAL_V2 scalar tags and bounded canonical row serialization."""
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
import re

import rfc8785

from vde.contracts import loads
from .errors import require, ExecutionError

REVISION = 'P4_INTERNAL_V2'
INTEGER = re.compile(r'(?:0|-?[1-9][0-9]*)', re.ASCII)
DECIMAL = re.compile(r'(?:0|-?(?:[1-9][0-9]*(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9]))', re.ASCII)


def decimal_text(value):
    require(value.is_finite(), 'SCHEMA_MISMATCH', 'Nonfinite Decimal')
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    text = '0' if value == 0 else text
    require(DECIMAL.fullmatch(text) is not None, 'SCHEMA_MISMATCH', 'Noncanonical Decimal wire')
    return text


def encode_cell(value):
    if value is None or type(value) in (str, bool):
        if type(value) is str:
            try:
                value.encode('utf-8', errors='strict')
            except UnicodeError as exc:
                raise ExecutionError('SCHEMA_MISMATCH', 'Invalid Unicode') from exc
        return value
    if type(value) is int:
        require(-(2**63) <= value <= 2**63-1, 'SCHEMA_MISMATCH', 'Integer outside signed64')
        return {'type': 'integer', 'value': str(value)}
    if type(value) is Decimal:
        return {'type': 'decimal', 'value': decimal_text(value)}
    if type(value) is datetime:
        require(value.tzinfo is not None and value.utcoffset().total_seconds() == 0
                and value.microsecond == 0, 'SCHEMA_MISMATCH', 'Datetime requires explicit UTC seconds')
        return {'type': 'datetime', 'value': value.isoformat(timespec='seconds').replace('+00:00', 'Z')}
    if type(value) is date:
        return {'type': 'date', 'value': value.isoformat()}
    if type(value) is time:
        require(value.tzinfo is None and value.microsecond == 0, 'SCHEMA_MISMATCH', 'Unsupported time')
        return {'type': 'time', 'value': value.isoformat(timespec='seconds')}
    raise ExecutionError('SCHEMA_MISMATCH', 'Unsupported scalar; no implicit conversion')


def decode_cell(cell, expected_type=None):
    if expected_type == 'integer':
        require(type(cell) is dict and cell.get('type') == 'integer', 'SCHEMA_MISMATCH', 'Integer tag required')
    if cell is None or type(cell) in (str, bool):
        encode_cell(cell)
        return cell
    require(type(cell) is dict and set(cell) == {'type', 'value'} and type(cell['value']) is str,
            'SCHEMA_MISMATCH', 'Invalid typed cell')
    kind, text = cell['type'], cell['value']
    try:
        if kind == 'integer':
            require(INTEGER.fullmatch(text) is not None, 'SCHEMA_MISMATCH', 'Noncanonical integer')
            value = int(text)
        elif kind == 'decimal':
            require(DECIMAL.fullmatch(text) is not None, 'SCHEMA_MISMATCH', 'Noncanonical decimal')
            value = Decimal(text)
        elif kind == 'date':
            value = date.fromisoformat(text)
        elif kind == 'datetime':
            require(text.endswith('Z'), 'SCHEMA_MISMATCH', 'UTC datetime required')
            value = datetime.fromisoformat(text.replace('Z', '+00:00'))
        elif kind == 'time':
            value = time.fromisoformat(text)
        else:
            raise ExecutionError('SCHEMA_MISMATCH', 'Unknown cell tag')
        require(encode_cell(value) == cell, 'SCHEMA_MISMATCH', 'Noncanonical typed cell')
        return value
    except (ValueError, OverflowError) as exc:
        raise ExecutionError('SCHEMA_MISMATCH', 'Invalid scalar spelling') from exc


def row_bytes(values):
    # Arrays compose canonical scalar encodings without re-encoding hundreds
    # of identical cells. The memo lives for one bounded row only, never for
    # a dataset/session. Every token still comes from the conforming library.
    tokens, local = [], {}
    for value in values:
        require(value is None or type(value) in (str, bool, int, Decimal, date, datetime, time),
                'SCHEMA_MISMATCH', 'Unsupported runtime scalar')
        key = type(value), value
        if key not in local:
            local[key] = rfc8785.dumps(encode_cell(value))
        tokens.append(local[key])
    return b'[' + b','.join(tokens) + b']'


def serialize(columns, rows, dataset_id, budget, sink=None):
    """Build only the P1-required opaque bytes, never a full object matrix."""
    header = dict(columns=list(columns), dataset_id=dataset_id, format_revision=REVISION, rows=[])
    output = bytearray() if sink is None else None

    def write(data):
        require(len(data) <= 8*1024*1024, 'SCHEMA_MISMATCH', 'Wire buffer exceeds limit')
        if sink is None:
            output.extend(data)
        else:
            budget.write(sink, data)

    write(rfc8785.dumps(header)[:-2])
    count = 0
    for row in rows:
        count += 1
        budget.shape(len(columns), count)
        if count > 1:
            write(b',')
        write(row_bytes(row.values))
        if count % 1000 == 0:
            budget.check()
    write(b']}')
    budget.check()
    return bytes(output) if output is not None else None, count


def iter_payload(data, *, expected_columns=None, dataset_id=None):
    """Strict canonical decode one row at a time; not a P5 QA/export engine."""
    prefix, separator, rest = data.partition(b',"rows":[')
    require(bool(separator), 'SCHEMA_MISMATCH', 'Invalid wire header')
    try:
        header = loads((prefix + b',"rows":[]}').decode('utf-8'))
        require(set(header) == {'columns', 'dataset_id', 'format_revision', 'rows'}
                and header['format_revision'] == REVISION, 'SCHEMA_MISMATCH', 'Unknown wire revision/keys')
        columns = header['columns']
        require(type(columns) is list and 0 < len(columns) <= 200
                and all(type(c) is str for c in columns) and len(set(columns)) == len(columns),
                'SCHEMA_MISMATCH', 'Invalid wire columns')
        require((expected_columns is None or columns == list(expected_columns))
                and (dataset_id is None or header['dataset_id'] == dataset_id), 'SCHEMA_MISMATCH', 'Wire identity mismatch')
        require(prefix + b',"rows":[]}' == rfc8785.dumps(header), 'SCHEMA_MISMATCH', 'Noncanonical wire header')
        # Find row boundaries respecting quoted strings and escapes. Decode a
        # single bounded row rather than loading all 20 million logical cells.
        position, count = 0, 0
        while rest[position:position+2] != b']}':
            require(rest[position:position+1] == b'[', 'SCHEMA_MISMATCH', 'Invalid row start')
            start, depth, quoted, escaped = position, 0, False, False
            while position < len(rest):
                char = rest[position]
                position += 1
                if quoted:
                    if escaped:
                        escaped = False
                    elif char == 92:
                        escaped = True
                    elif char == 34:
                        quoted = False
                elif char == 34:
                    quoted = True
                elif char in (91, 123):
                    depth += 1
                elif char in (93, 125):
                    depth -= 1
                    if depth == 0:
                        break
                require(position-start <= 8*1024*1024, 'SCHEMA_MISMATCH', 'Wire row exceeds buffer')
            raw = rest[start:position]
            cells = loads(raw.decode('utf-8'))
            require(type(cells) is list and len(cells) == len(columns), 'SCHEMA_MISMATCH', 'Wire row shape')
            values = tuple(decode_cell(c) for c in cells)
            require(row_bytes(values) == raw, 'SCHEMA_MISMATCH', 'Noncanonical wire row')
            count += 1
            require(count <= 100000, 'SCHEMA_MISMATCH', 'P4_ROW_LIMIT')
            yield values
            if rest[position:position+1] == b',':
                position += 1
                require(rest[position:position+1] == b'[', 'SCHEMA_MISMATCH', 'Trailing comma')
            else:
                break
        require(rest[position:] == b']}', 'SCHEMA_MISMATCH', 'Wire trailing/truncated data')
    except (ValueError, KeyError, TypeError, UnicodeError, rfc8785.CanonicalizationError) as exc:
        raise ExecutionError('SCHEMA_MISMATCH', 'Invalid canonical payload') from exc
