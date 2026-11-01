"""P4 failures mapped to the unchanged P0 execution_error contract."""
from uuid import uuid4

from vde.contracts import validate
from vde.errors import utc_now


class ExecutionError(Exception):
    def __init__(self, code, reason, *, operation=None, column=None, row_id=None, value=None, stage=None):
        self.code, self.reason = code, reason
        self.operation, self.column = operation, column
        self.row_id, self.value, self.stage = row_id, value, stage
        super().__init__(reason)

    def public(self, *, order_id=None, run_id=None, source_id=None):
        if self.code == 'STORAGE_ERROR':
            category, stage = 'STORAGE', 'STORAGE'
        elif self.code == 'STATE_INVALID_TRANSITION':
            category, stage = 'STATE', 'ORDER'
        elif self.code in {'APPROVAL_MISSING', 'APPROVAL_HASH_MISMATCH', 'VERSION_INCOMPATIBLE'}:
            category, stage = 'APPROVAL', 'APPROVAL'
        elif self.code.startswith('VALIDATION_') or self.code in {'INVALID_PARAMETER', 'INVALID_OPERATION'}:
            category, stage = 'VALIDATION', 'TRANSFORMATION_VALIDATION'
        elif self.code in {'INPUT_NOT_FOUND', 'INPUT_UNREADABLE', 'XLSX_FORMULA_CACHE_MISSING'}:
            category, stage = 'INGESTION', 'INGESTION'
        else:
            category, stage = 'TRANSFORMATION', self.stage or 'TRANSFORMATION'
        op = self.operation or {}
        details = {'reason': self.reason[:1000]}
        if self.row_id is not None:
            details['value'] = str(self.value)[:500]
        document = dict(schema_version='1.1', error_id=str(uuid4()), code=self.code,
                        category=category, stage=stage, severity='BLOCKER',
                        message='Deterministic transformation rejected.', details=details,
                        order_id=order_id, run_id=run_id, source_id=source_id,
                        operation_id=op.get('operation_id'), dataset_id=op.get('input_dataset'),
                        column=self.column, row_ids=[] if self.row_id is None else [str(self.row_id)],
                        retryable=False, created_at=utc_now())
        validate(document, 'execution_error')
        return document


def require(condition, code, reason, **context):
    if not condition:
        raise ExecutionError(code, reason, **context)
