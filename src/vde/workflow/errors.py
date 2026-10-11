"""Internal workflow failures using only the frozen P0 public error contract."""
from uuid import uuid4
from vde.contracts import validate
from vde.errors import utc_now


class WorkflowError(Exception):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(reason)

    def public(self, *, order_id=None, source_id=None):
        if self.code.startswith('VALIDATION_') or self.code in {'INVALID_OPERATION', 'INVALID_PARAMETER'}:
            category = 'VALIDATION'
            stage = 'BRIEF_VALIDATION' if self.code in {'VALIDATION_BRIEF_SCHEMA', 'VALIDATION_ACCEPTANCE_CRITERION'} else 'TRANSFORMATION_VALIDATION'
        elif self.code == 'STATE_INVALID_TRANSITION':
            category, stage = 'STATE', 'ORDER'
        elif self.code == 'INPUT_NOT_FOUND':
            category, stage = 'INGESTION', 'INGESTION'
        else:
            category, stage = 'APPROVAL', 'APPROVAL'
        document = dict(schema_version='1.1', error_id=str(uuid4()), code=self.code,
                        category=category, severity='BLOCKER', stage=stage,
                        message='Manual workflow command rejected.',
                        details={'reason': self.reason[:1000]}, order_id=order_id,
                        run_id=None, source_id=source_id, operation_id=None,
                        dataset_id=None, column=None, row_ids=[], retryable=False,
                        created_at=utc_now())
        validate(document, 'execution_error')
        return document


def require(condition, code, reason):
    if not condition:
        raise WorkflowError(code, reason)
