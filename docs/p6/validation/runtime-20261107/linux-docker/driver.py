"""Disposable simulated explicit operator actions inside a Linux container."""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, '/tmp/code/tests/p6')
from conftest import (UIScenario, canonical, download_http, new_app,
                      payload_hashes, snapshot, widget)
from vde.bootstrap import bootstrap
from vde.config import Config

EVIDENCE = Path('/evidence')
DATA = Path('/data')
mode = sys.argv[1]
generator = download_http.__wrapped__()
fetch = next(generator)
try:
    if mode == 'create':
        assert not (DATA / 'app.sqlite3').exists(), 'Smoke requires empty disposable data mount'
        case = UIScenario(DATA)
        prepared = case.prepare_ui()
        assert case.order().status == 'READY'
        result = fetch(case.app.get('download_button')[0].proto.url)
        report = fetch(case.app.get('download_button')[1].proto.url)
        expected = (Path('/tmp/code/pecs/pilot_slice_v1/fixtures/P-A_dirty_csv') / 'expected_result.csv').read_bytes()
        assert len(expected) == 277
        assert result.code == report.code == 200
        assert result.body == expected
        assert hashlib.sha256(result.body).hexdigest() == prepared.view.artifact.checksum
        assert result.headers['Content-Type'] == 'text/csv'
        assert result.headers['Content-Disposition'] == f'attachment; filename="{prepared.result_name}"'
        assert int(result.headers['Content-Length']) == len(result.body)
        assert report.headers['Content-Type'] == 'application/json; charset=utf-8'
        assert report.headers['Content-Disposition'] == f'attachment; filename="{prepared.report_name}"'
        assert int(report.headers['Content-Length']) == len(report.body)
        qa = json.loads(report.body)
        assert qa['overall_status'] == 'PASS'
        assert qa == prepared.view.report
        before = {'rows': snapshot(DATA), 'payload_hashes': payload_hashes(DATA),
                  'order_id': case.order_id, 'run_id': case.run_id,
                  'result_sha256': hashlib.sha256(result.body).hexdigest(),
                  'result_size': len(result.body),
                  'result_headers': dict(result.headers), 'report_headers': dict(report.headers),
                  'platform': sys.platform,
                  'simulated_explicit_test_user_approvals_only': True}
        (EVIDENCE / 'before-restart.json').write_text(json.dumps(before, indent=2) + '\n')
        (EVIDENCE / 'saved-result.csv').write_bytes(result.body)
        (EVIDENCE / 'saved-qa.json').write_bytes(report.body)
        print(json.dumps({'mode': mode, 'health': case.env.health,
                          'result_sha256': before['result_sha256'],
                          'result_size': before['result_size'],
                          'row_counts': {k:len(v) for k,v in before['rows'].items()}}))
    elif mode == 'restart':
        before = json.loads((EVIDENCE / 'before-restart.json').read_text())
        env = bootstrap(Config(DATA))
        assert env.health == 'ready'
        assert snapshot(DATA) == before['rows']
        assert payload_hashes(DATA) == before['payload_hashes']
        app = new_app(DATA)
        assert 'p6_delivery_snapshot' not in app.session_state
        assert len(app.get('download_button')) == 0
        widget(app, 'selectbox', 'Download Order').set_value(before['order_id']).run()
        widget(app, 'selectbox', 'Download Run').set_value(before['run_id']).run()
        assert not app.exception
        assert len(app.get('download_button')) == 0
        widget(app, 'button', 'Prepare verified download').click().run()
        assert not app.exception
        response = fetch(app.get('download_button')[0].proto.url)
        assert response.code == 200
        assert response.body == (EVIDENCE / 'saved-result.csv').read_bytes()
        assert hashlib.sha256(response.body).hexdigest() == before['result_sha256']
        assert snapshot(DATA) == before['rows']
        assert payload_hashes(DATA) == before['payload_hashes']
        result = {'mode': mode, 'health': env.health,
                  'persisted_rows_exactly_unchanged': True,
                  'persisted_payload_hashes_exactly_unchanged': True,
                  'fresh_session_had_no_prepared_download': True,
                  'explicit_reprepare_http_get_status': response.code,
                  'result_sha256': hashlib.sha256(response.body).hexdigest(),
                  'platform': sys.platform,
                  'actual_mac_host_execution': 'NOT_RUN'}
        (EVIDENCE / 'after-restart.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
    else:
        raise ValueError(mode)
finally:
    generator.close()
