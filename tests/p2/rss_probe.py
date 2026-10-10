"""Independent fresh Linux process: include upload/read buffers in measured peak."""
import gc
import hashlib
import io
import json
from pathlib import Path
import platform
import resource
import sys
import threading
import zipfile

from vde.bootstrap import bootstrap
from vde.config import Config
from vde.models import OrderRecord
from vde.persistence.uow import UnitOfWork
from vde.ingestion.local import LocalIngestion
from vde.ingestion.limits import current_rss

pack, work, kind = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
env = bootstrap(Config(work))
assert env.health == 'ready'
with UnitOfWork(env.database, env.workspace) as uow:
    uow.orders.add(OrderRecord('order-stress', 'Memory test', 'synthetic', '2026-10-11T00:00:00Z', '2026-10-11T00:00:00Z'))
service = LocalIngestion(env)
gc.collect()
baseline = current_rss()
peak = [baseline]
stop = threading.Event()


def sample():
    while not stop.wait(0.005):
        peak[0] = max(peak[0], current_rss())


thread = threading.Thread(target=sample, daemon=True)
thread.start()
try:
    if kind == 'csv':
        # 99,000,880 B, 198 columns, exactly 100k rows, no giant committed fixture.
        header = (','.join('H' + str(n) for n in range(198)) + '\n').encode()
        raw = header + (b'abcd,' * 197 + b'abcd\n') * 100000
        assert len(raw) <= 100_000_000
        service.register_local_asset('order-stress', 'stress.csv', raw, 'asset-stress')
        result = service.preview_csv('order-stress', 'asset-stress', 'UTF-8', ',', 0)
    else:
        # Reduce the approved over-row fixture to exactly the inclusive 100k cap.
        source = pack / 'fixtures/new_xlsx/rows_over_100000.xlsx'
        out = io.BytesIO()
        with zipfile.ZipFile(source) as z, zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as target:
            for info in z.infolist():
                data = z.read(info)
                if info.filename == 'xl/worksheets/sheet1.xml':
                    start = data.index(b'<row r="100002"')
                    end = data.index(b'</row>', start) + len(b'</row>')
                    data = data[:start] + data[end:]
                target.writestr(info.filename, data)
        raw = out.getvalue()
        del data, out
        service.register_local_asset('order-stress', 'stress.xlsx', raw, 'asset-stress')
        result = service.preview_xlsx('order-stress', 'asset-stress', 'Orders')
    peak[0] = max(peak[0], current_rss())
    # Linux ru_maxrss uses KiB and independently catches between-sample peaks.
    kernel_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    observed_peak = max(peak[0], kernel_peak)
    print(json.dumps({'platform': platform.platform(), 'python': platform.python_version(),
                      'openpyxl': __import__('openpyxl').__version__, 'kind': kind,
                      'measurement': 'Linux VmRSS 5ms samples and ru_maxrss KiB * 1024; fresh process',
                      'baseline_bytes': baseline, 'sampled_peak_bytes': peak[0],
                      'kernel_peak_bytes': kernel_peak, 'incremental_peak_bytes': observed_peak - baseline,
                      'limit_bytes': 536870912, 'raw_size_bytes': len(raw),
                      'raw_sha256': hashlib.sha256(raw).hexdigest(),
                      'data_row_count': result.data_row_count, 'column_count': result.column_count,
                      'first_rows_count': len(result.first_rows), 'dataset_handle': hasattr(result, 'dataset')}))
finally:
    stop.set()
    thread.join()
