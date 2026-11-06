"""Read-only source compatibility probe; NOT a P5 exporter or approval.

Execute with the frozen checkout's src/ and tests/ in PYTHONPATH. The existing
P4 test helper creates isolated local fixtures and simulated test approvals.
No repository file, live Order, P0 fixture or historical evidence is changed.
"""
import argparse
import csv
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from p4.support import Approved
from vde.execution.service import ExecutionService
from vde.execution.wire import decode_cell, decimal_text

BASE = 'fd39aa1bed480313504ae8b1f76e77e170cb72ba'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def csv_v02a(value):
    # Exact Q03 runtime-type dispatch. Deliberately no schema-driven widening.
    if value is None:
        return ''
    if type(value) is int:
        assert -(2**63) <= value < 2**63
        return str(value)
    if type(value) is Decimal:
        d = decimal_text(value)
        return d if '.' in d else d+'.0'
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) in (date, datetime, time):
        return value.isoformat().replace('+00:00', 'Z')
    assert type(value) is str
    return value


def run(repo, out):
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    assert head == BASE, 'This reproduction must use the exact approved historical base'
    import vde.execution.service as source_module
    assert Path(source_module.__file__).is_relative_to(repo), 'Runtime must come from the specified real checkout'
    summary = {'classification':'BLOCKING_P4_P5_NUMERIC_CONTRACT_CONFLICT',
               'runtime_commit':head,
               'runtime_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=repo,text=True).strip(),
               'test_only_approval_notice':'Existing P4 helper simulates P3 approval in disposable fixture DBs; no real business Approval is represented.',
               'p5_runtime_tests_executed':False,'cases':[]}
    suite = ET.Element('testsuite',name='P5_preimplementation_numeric_contract_compatibility',tests='2',failures='2',errors='0',skipped='0')
    for name, fixture, expected_count in [('P-A','P-A_dirty_csv',1),('P-B','P-B_xlsx_sheet',4)]:
        with tempfile.TemporaryDirectory(prefix='vde-p5-contract-probe-') as directory:
            scenario = Approved(directory, fixture)
            service = ExecutionService(scenario.env)
            result = service.execute(scenario.order_id,scenario.order(),scenario.handoff)
            handle, raw = service.read_result(result.run_id)
            assert hashlib.sha256(raw).hexdigest()==handle.checksum
            with scenario.uow() as uow:
                spec = uow.specs.get(scenario.handoff.transformation_spec_version_id).document_json
                brief = uow.briefs.get(scenario.handoff.brief_version_id).document_json
            fields = {f['name']:f for f in spec['expected_schema']}
            names = spec['output']['column_order']
            wire = json.loads(raw)
            rows = [[decode_cell(v) for v in row] for row in wire['rows']]
            mismatches = []
            for row_index,(row,wire_row) in enumerate(zip(rows,wire['rows']),1):
                for column,value,tag in zip(names,row,wire_row):
                    if fields[column]['data_type']=='decimal' and type(value) is int:
                        mismatches.append(dict(row=row_index,column=column,declared_type='decimal',
                                               actual_runtime_type='int',actual_wire_tag=tag,
                                               q03_actual_csv=csv_v02a(value),
                                               frozen_golden_required_csv=csv_v02a(Decimal(value))))
            assert len(mismatches)==expected_count
            stream = io.StringIO(newline='')
            writer = csv.writer(stream,lineterminator='\n')
            writer.writerow([fields[n]['output_name'] for n in names])
            writer.writerows([[csv_v02a(v) for v in row] for row in rows])
            projected = stream.getvalue().encode('utf-8')
            source = repo/'pecs/pilot_slice_v1/fixtures'/fixture
            golden = (source/'expected_result.csv').read_bytes()
            assert projected != golden
            (out/(name+'.P4_INTERNAL_V2.json')).write_bytes(raw)
            (out/(name+'.q03_runtime_type_projection.TEST_ONLY.csv')).write_bytes(projected)
            (out/(name+'.frozen_golden.snapshot.csv')).write_bytes(golden)
            case = dict(fixture=name,source_fixture=fixture,internal_checksum=handle.checksum,
                        rows=handle.row_count,columns=list(handle.columns),mismatched_cells=mismatches,
                        projected_csv_sha256=sha(projected),projected_csv_size=len(projected),
                        frozen_golden_sha256=sha(golden),frozen_golden_size=len(golden),
                        full_csv_equality='FAIL',strict_declared_decimal_type='FAIL',
                        p4_run_status='succeeded',order_status=scenario.order().status,
                        source_input_unchanged=scenario.env.workspace.path(scenario.asset.workspace_relpath).read_bytes()==scenario.raw,
                        frozen_spec_refs=spec['acceptance_criteria_ref'],production_export_performed=False)
            summary['cases'].append(case)
            check = ET.SubElement(suite,'testcase',classname='contract_compatibility',name=name+'_actual_P4_vs_P5_v02a')
            failure = ET.SubElement(check,'failure',type='ContractCompatibilityError',message='Integer tags in approved decimal fields conflict with strict P5 v0.2a type dispatch and golden spelling.')
            failure.text=json.dumps(case,ensure_ascii=False,indent=2)
    (out/'NUMERIC_HANDOFF_FINDINGS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    ET.ElementTree(suite).write(out/'numeric-compatibility.junit.xml',encoding='utf-8',xml_declaration=True)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    # Deliberate nonzero outcome: these are real blocking contract conflicts,
    # not PASS, skip, xfail or historical whole-application scope exceptions.
    return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(run(args.repo.resolve(),args.out.resolve()))
