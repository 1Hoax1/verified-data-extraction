"""P5 diagnostics use only the existing P0 public error vocabulary."""
from uuid import uuid4
from vde.contracts import validate
from vde.errors import utc_now


class P5Error(Exception):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(reason)

    def public(self, *, order_id=None, run_id=None):
        category, stage = {
            'EXPORT_FAILED': ('EXPORT', 'EXPORT'),
            'ROUNDTRIP_MISMATCH': ('EXPORT', 'ROUNDTRIP'),
            'QA_BLOCKER': ('QA', 'QA'),
            'STORAGE_ERROR': ('STORAGE', 'STORAGE'),
            'STATE_INVALID_TRANSITION': ('STATE', 'ORDER'),
            'APPROVAL_MISSING': ('APPROVAL', 'APPROVAL'),
            'APPROVAL_HASH_MISMATCH': ('APPROVAL', 'APPROVAL'),
            'VERSION_INCOMPATIBLE': ('APPROVAL', 'APPROVAL'),
        }.get(self.code, ('VALIDATION', 'PREFLIGHT'))
        record = dict(schema_version='1.1', error_id=str(uuid4()), code=self.code,
                      category=category, severity='BLOCKER', stage=stage,
                      message='Export or deterministic QA rejected.',
                      details={'reason': self.reason[:1000]}, order_id=order_id,
                      run_id=run_id, source_id=None, operation_id=None,
                      dataset_id=None, column=None, row_ids=[], retryable=False,
                      created_at=utc_now())
        validate(record, 'execution_error')
        return record


def require(condition, code, reason):
    if not condition:
        raise P5Error(code, reason)
