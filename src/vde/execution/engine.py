"""One streaming linear dataset; bounded external sort/deduplicate only."""
from dataclasses import dataclass

from .operations import plan_columns, apply_one
from .spill import external_sort, sort_key, deduplicate


@dataclass
class Table:
    columns: tuple
    rows: object
    audit: list


def validate_columns(columns, pipeline):
    current = tuple(columns)
    for op in pipeline:
        current = plan_columns(current, op)
    return current


def _stage(columns, rows, op, audit, budget, scratch):
    def counted():
        for row in rows:
            audit['input_rows'] += 1
            if audit['input_rows'] % 1000 == 0:
                budget.check()
            yield row

    kind = op['type']
    if kind == 'sort':
        result = external_sort(counted(), sort_key(columns, op['params']), scratch, budget)
    elif kind == 'deduplicate':
        result = deduplicate(counted(), columns, op['params'], scratch, budget, audit)
    else:
        result = (output for row in counted() if (output := apply_one(columns, row, op, audit)) is not None)
    try:
        for row in result:
            audit['output_rows'] += 1
            budget.shape(len(row.values), audit['output_rows'])
            yield row
    finally:
        result.close()
        audit['deleted_rows'] = audit['input_rows']-audit['output_rows']


def apply(plan, row_stream, budget, scratch):
    columns, rows, audits = tuple(row_stream.columns), row_stream.rows, []
    for op in plan.pipeline:
        output = plan_columns(columns, op)
        audit = dict(operation_id=op['operation_id'], type=op['type'],
                     input_dataset=op['input_dataset'], output_dataset=op['output_dataset'],
                     input_rows=0, output_rows=0, deleted_rows=0, deleted_row_sample=[],
                     parse_failed_count=0, parse_failed_sample=[])
        audits.append(audit)
        rows = _stage(columns, rows, op, audit, budget, scratch)
        columns = output
    return Table(columns, rows, audits)
