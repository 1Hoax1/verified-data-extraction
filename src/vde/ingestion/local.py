"""Existing-Order use cases over unchanged P1 repositories and Storage."""
from pathlib import Path
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from vde.errors import StorageError
from .diagnostics import require
from .limits import Budget, raw_check
from .csv_reader import read_csv, options
from .xlsx_reader import read_xlsx, list_sheets


def source_type(filename):
    suffix = Path(filename).suffix.lower()
    require(suffix in ('.csv', '.xlsx'), 'UNSUPPORTED_EXTENSION', 'UNSUPPORTED_FORMAT')
    return 'LOCAL_CSV' if suffix == '.csv' else 'LOCAL_XLSX'


class LocalIngestion:
    def __init__(self, bootstrap_result, *, allow_degraded_read=False, storage=None):
        self.env = bootstrap_result
        self.allow_degraded_read = allow_degraded_read
        self.storage = storage or Storage(self.env.database, self.env.workspace)

    def _health(self, write=False):
        if self.env.health == 'blocked' or (self.env.health != 'ready' and
                (write or not self.allow_degraded_read)):
            raise StorageError('P2 operation blocked by workspace health; no repair attempted')

    def orders(self):
        self._health()
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            return uow.orders.list()

    def assets(self, order_id):
        self._health()
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            return uow.inputs.list_for_order(order_id)

    def register_local_asset(self, order_id, filename, raw_bytes, asset_id):
        self._health(write=True)
        source_type(filename)
        raw_check(raw_bytes)
        budget = Budget()
        budget.check()
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            require(any(o.id == order_id for o in uow.orders.list()), 'ORDER_NOT_FOUND', 'INPUT_NOT_FOUND')
        result = self.storage.register_input(id=asset_id, order_id=order_id,
                                             original_filename=filename, data=raw_bytes)
        budget.check()
        return result

    def read_verified_asset(self, order_id, asset_id, *, budget=None):
        self._health()
        budget = budget or Budget()
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            records = uow.inputs.list_for_order(order_id)
            record = next((r for r in records if r.id == asset_id), None)
            require(record is not None, 'ASSET_NOT_FOUND_OR_NOT_OWNED', 'INPUT_NOT_FOUND')
        raw = self.storage.read_input(asset_id)
        raw_check(raw)
        budget.check()
        return raw, record

    def list_xlsx_sheets(self, order_id, asset_id):
        budget = Budget()
        raw, record = self.read_verified_asset(order_id, asset_id, budget=budget)
        require(source_type(record.original_filename) == 'LOCAL_XLSX', 'EXPECTED_XLSX', 'UNSUPPORTED_FORMAT')
        return list_sheets(raw, budget=budget)

    def preview_csv(self, order_id, asset_id, encoding, delimiter, header_row):
        options(encoding, delimiter, header_row)
        budget = Budget()
        raw, record = self.read_verified_asset(order_id, asset_id, budget=budget)
        require(source_type(record.original_filename) == 'LOCAL_CSV', 'EXPECTED_CSV', 'UNSUPPORTED_FORMAT')
        return read_csv(raw, asset_id=asset_id, encoding=encoding, delimiter=delimiter,
                        header_row=header_row, byte_sha256=record.byte_sha256, budget=budget)

    def preview_xlsx(self, order_id, asset_id, sheet_name):
        require(isinstance(sheet_name, str) and sheet_name, 'SHEET_REQUIRED')
        budget = Budget()
        raw, record = self.read_verified_asset(order_id, asset_id, budget=budget)
        require(source_type(record.original_filename) == 'LOCAL_XLSX', 'EXPECTED_XLSX', 'UNSUPPORTED_FORMAT')
        return read_xlsx(raw, asset_id=asset_id, sheet_name=sheet_name,
                         byte_sha256=record.byte_sha256, budget=budget)
