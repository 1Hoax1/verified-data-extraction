"""Bounded local external ordering. JSON records never execute stored code."""
from contextlib import ExitStack
from dataclasses import replace
import heapq
import itertools
import json
from pathlib import Path
from uuid import uuid4

from vde.ingestion.limits import current_rss
from .errors import require
from .source_adapter import Row
from .wire import encode_cell, decode_cell


class Descending:
    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self.value > other.value

    def __eq__(self, other):
        return self.value == other.value


def sort_key(columns, params):
    indices = [columns.index(c) for c in params['by']]
    types = [None] * len(indices)

    def key(row):
        result = []
        for n, (index, ascending) in enumerate(zip(indices, params['ascending'])):
            value = row.values[index]
            if value is None:
                result.append((0 if params['nulls'] == 'FIRST' else 1, 0))
            else:
                if types[n] is None:
                    types[n] = type(value)
                require(type(value) is types[n], 'SCHEMA_MISMATCH', 'Mixed sort key types')
                result.append((1 if params['nulls'] == 'FIRST' else 0, value if ascending else Descending(value)))
        return tuple(result)
    return key


def _record(position, row):
    data = json.dumps([position, row.source, row.ordinal, [encode_cell(v) for v in row.values]],
                      ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8') + b'\n'
    require(len(data) <= 8*1024*1024, 'SCHEMA_MISMATCH', 'Spill row exceeds buffer')
    return data


def external_sort(rows, key, directory, budget):
    files, chunk, size = [], [], 0
    chunk_rss = current_rss()

    def path():
        return Path(directory) / (str(uuid4()) + '.rows')

    def write(target, entries):
        with target.open('xb', buffering=1024*1024) as stream:
            for index, entry in enumerate(entries):
                raw = entry[3]
                budget.reserve(len(raw))
                stream.write(raw)
                if index % 1000 == 0:
                    budget.check()

    def read(stream):
        for index, raw in enumerate(stream):
            require(len(raw) <= 8*1024*1024, 'SCHEMA_MISMATCH', 'Spill record size')
            position, source, ordinal, cells = json.loads(raw)
            row = Row(source, tuple(decode_cell(c) for c in cells), ordinal)
            if index % 1000 == 0:
                budget.check()
            yield key(row), position, row, raw

    def remove(paths):
        for item in paths:
            budget.release(item.stat().st_size)
            item.unlink()

    def merged(paths):
        require(len(paths) <= 16, 'STORAGE_ERROR', 'P4_MERGE_FAN_IN')
        budget.merge_fan_in = max(budget.merge_fan_in, len(paths))
        with ExitStack() as stack:
            streams = [read(stack.enter_context(p.open('rb', buffering=1024*1024))) for p in paths]
            yield from heapq.merge(*streams, key=lambda entry: (entry[0], entry[1]))

    try:
        for position, row in enumerate(rows):
            encoded = _record(position, row)
            chunk.append((key(row), position, row, encoded))
            size += len(encoded)
            if size >= 4*1024*1024 or current_rss()-chunk_rss >= 16*1024*1024:
                chunk.sort(key=lambda e: (e[0], e[1]))
                target = path()
                files.append(target)
                write(target, chunk)
                chunk, size = [], 0
                chunk_rss = current_rss()
        if not files:
            chunk.sort(key=lambda e: (e[0], e[1]))
            for entry in chunk:
                yield entry[2]
            return
        if chunk:
            chunk.sort(key=lambda e: (e[0], e[1]))
            target = path()
            files.append(target)
            write(target, chunk)
            chunk = []
        while len(files) > 16:
            following = []
            for offset in range(0, len(files), 16):
                group = files[offset:offset+16]
                target = path()
                write(target, merged(group))
                following.append(target)
                remove(group)
            files = following
        for entry in merged(files):
            yield entry[2]
    finally:
        for item in files:
            if item.exists():
                budget.release(item.stat().st_size)
                item.unlink()


def deduplicate(rows, columns, params, directory, budget, audit):
    indices = [columns.index(c) for c in params['subset']]

    def key(row):
        # Type tags distinguish integer, Decimal, bool and string; no NFC.
        return json.dumps([encode_cell(row.values[i]) for i in indices], ensure_ascii=False,
                          sort_keys=True, separators=(',', ':'))

    numbered = (replace(row, ordinal=position) for position, row in enumerate(rows))
    ordered = external_sort(numbered, key, directory, budget)

    def survivors():
        for _, group in itertools.groupby(ordered, key):
            chosen, count = None, 0
            for row in group:
                count += 1
                if chosen is None or params['keep'] == 'LAST':
                    dropped, chosen = chosen, row
                else:
                    dropped = row
                if dropped is not None and len(audit['deleted_row_sample']) < 20:
                    audit['deleted_row_sample'].append(dropped.source)
            if params['keep'] != 'NONE' or count == 1:
                yield chosen
            elif len(audit['deleted_row_sample']) < 20:
                audit['deleted_row_sample'].append(chosen.source)

    restored = external_sort(survivors(), lambda row: row.ordinal, directory, budget)
    for row in restored:
        yield replace(row, ordinal=None)
