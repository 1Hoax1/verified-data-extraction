"""Independent positive 100k x 200 P4 workload and streaming reference oracle."""
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time

import rfc8785
from vde.execution.service import ExecutionService
from vde.execution.wire import iter_payload
from vde.ingestion.limits import current_rss
from .support import Approved, fields_for_stress, stress_pipeline


def main():
    pack, directory = Path(sys.argv[1]), Path(sys.argv[2])
    directory.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('approved_stress_generator', pack/'tools/generate_p4_stress_fixture.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    source = directory/'dense.csv'
    generated = generator.generate(source, 100000, 200, 37, 90000)
    assert generated['sha256'] == '5c5d2dbf69c0b8f4d27be5ec8a258677eb883d5ad267a4ec644b0205978aa97d'
    a = Approved(directory/'approved', raw=source.read_bytes(), fields=fields_for_stress(), pipeline=stress_pipeline(),
                 csv_options={'encoding': 'UTF-8', 'delimiter': ',', 'header_row': 0})
    del a.raw
    gc.collect()
    baseline = current_rss()
    peak, stop = [baseline], threading.Event()

    def sample():
        while not stop.wait(0.005):
            peak[0] = max(peak[0], current_rss())

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    service = ExecutionService(a.env)
    started = time.monotonic()
    try:
        result = service.execute(a.order_id, a.order(), a.handoff)
        elapsed = time.monotonic()-started
    finally:
        stop.set()
        thread.join()
    observed = max(peak[0], resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    assert observed-baseline <= 536870912
    assert elapsed <= 120
    with a.uow() as uow:
        metrics = uow.runs.get(result.run_id).metrics_json
    assert metrics['resources']['scratch_peak_bytes'] <= 2147483648
    assert metrics['resources']['merge_fan_in'] <= 16
    handle, payload = service.read_result(result.run_id)
    assert len(handle.columns) == 200 and handle.row_count == 90000
    # Independent fixed-fixture ASCII reference: no execution.engine/operations
    # in the oracle; derive source indices by modular arithmetic.
    inverse = pow(37, -1, 100000)
    seen, count = set(), 0
    reference = hashlib.sha256()
    header = dict(columns=[f'c{i:03}' for i in range(200)], dataset_id='result', format_revision='P4_INTERNAL_V2', rows=[])
    reference.update(rfc8785.dumps(header)[:-2])
    actual = iter(iter_payload(payload, expected_columns=header['columns'], dataset_id='result'))
    for key in range(100000):
        r = inverse*key % 100000
        identity = r % 90000
        if identity in seen:
            continue
        seen.add(identity)
        wanted = (f'{key:05d}', identity)+('0',)*198
        assert next(actual) == wanted
        if count:
            reference.update(b',')
        reference.update(b'["'+f'{key:05d}'.encode()+b'",{"type":"integer","value":"'+str(identity).encode()+b'"}'+b',"0"'*198+b']')
        count += 1
    reference.update(b']}')
    assert next(actual, None) is None and count == 90000
    assert reference.hexdigest() == handle.checksum == hashlib.sha256(payload).hexdigest()
    size, raw_sha = a.env.workspace.inspect(a.asset.workspace_relpath)
    assert raw_sha == generated['sha256'] and size == generated['byte_size']
    print(json.dumps(dict(result='PASS', tested_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_bytes=size, source_sha256=raw_sha, input_rows=100000, columns=200, result_rows=count,
        full_reference_cells_checked=count*200, result_sha256=handle.checksum,
        elapsed_seconds=elapsed, baseline_rss_bytes=baseline, observed_peak_rss_bytes=observed,
        incremental_peak_rss_bytes=observed-baseline, runtime_resources=metrics['resources']), indent=2))


if __name__ == '__main__':
    main()
