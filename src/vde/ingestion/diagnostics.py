"""P2 diagnostics, validated against the frozen P0 contract."""
from uuid import uuid4
from vde.contracts import validate
from vde.errors import utc_now


def diagnostic(code, reason, *, order_id=None, source_id=None):
    document = {
        'schema_version': '1.1', 'error_id': str(uuid4()), 'code': code,
        'category': 'INGESTION',
        'severity': 'WARNING' if code == 'XLSX_FORMULA_PRESENT' else 'BLOCKER',
        'stage': 'INGESTION', 'message': 'Local input read diagnostic.',
        'details': {'reason': reason[:1000]}, 'order_id': order_id,
        'run_id': None, 'source_id': source_id, 'operation_id': None,
        'dataset_id': None, 'column': None, 'row_ids': [], 'retryable': False,
        'created_at': utc_now(),
    }
    validate(document, 'execution_error')
    return document


class IngestionError(Exception):
    def __init__(self, reason, code='INPUT_UNREADABLE'):
        self.reason, self.code = reason, code
        super().__init__(reason)

    def public(self, *, order_id=None, source_id=None):
        return diagnostic(self.code, self.reason, order_id=order_id, source_id=source_id)


def require(condition, reason, code='INPUT_UNREADABLE'):
    if not condition:
        raise IngestionError(reason, code)
