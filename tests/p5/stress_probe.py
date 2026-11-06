"""Actual P1/P3/P4→P5 100000×200 success, independent streaming oracle."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from threading import Event,Thread
from time import monotonic
import csv
from openpyxl import load_workbook
from vde.bootstrap import bootstrap
from vde.config import Config
from vde.ingestion.limits import current_rss
from vde.p5.service import P5Service
from vde.p5.errors import P5Error
from .support import Scenario,field,simple_change,ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--design-root',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--format',choices=('CSV','XLSX'),required=True);p.add_argument('--negative-oversized',action='store_true')
    a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    source=a.directory/'fixed.csv'
    generator=[sys.executable,str(a.design_root/'tools/generate_p5_stress.py'),'--rows','100000','--columns','200','--format','CSV','--out',str(source)]
    generated=subprocess.run(generator,capture_output=True,text=True,check=True)
    identity=json.loads(generated.stdout)
    assert identity['size_bytes']==40500998 and identity['sha256']=='353698a4bab0ffc54633cb3fabad7eb404821b5f97dfeb7eb9676dafec4d9239'
    fields=[field('id',unique=True)]+[field(f'c{i:03d}') for i in range(1,200)]
    change=simple_change(fields,a.format,rows=100000)
    if a.negative_oversized:
        base_change=change
        def change(b,s):
            base_change(b,s)
            s['pipeline']=[dict(schema_version='1.1',operation_id='expand-approved-text',type='replace',
                input_dataset='raw',output_dataset='expanded',
                params=dict(columns=[f'c{i:03d}' for i in range(1,200)],old='x',new='x'*12)),
                dict(schema_version='1.1',operation_id='select-expanded',type='select_columns',
                input_dataset='expanded',output_dataset='result',params={'columns':['id']+[f'c{i:03d}' for i in range(1,200)]})]
    scenario=Scenario(a.directory/'approved-test-order',raw=source.read_bytes(),change=change)
    with scenario.uow() as u:
        run_before=u.runs.get(scenario.run_id);internal=u.artifacts.list_for_run(scenario.run_id)[0]
    p4_identity=scenario.env.workspace.inspect(internal.workspace_relpath)
    # Both independently approved Orders use the pinned CSV source and distinct
    # approved output formats. This is export stress, not an XLSX input claim.
    del scenario.raw
    gc.collect()
    baseline=current_rss();peak=[baseline];stop=Event();samples=[0]
    def sample():
        while not stop.wait(0.005):
            peak[0]=max(peak[0],current_rss());samples[0]+=1
    thread=Thread(target=sample,daemon=True);thread.start();started=monotonic()
    try:
        try:
            decision=P5Service(scenario.env).complete(scenario.run_id,scenario.order())
            assert not a.negative_oversized,'Oversized negative unexpectedly completed'
        except P5Error as error:
            assert a.negative_oversized and error.code=='EXPORT_FAILED'
            assert p4_identity[0]*2>536870912
            assert scenario.order().status=='FAILED' and scenario.delta()['artifacts']==0 and scenario.delta()['qa_reports']==0
            assert scenario.env.workspace.inspect(internal.workspace_relpath)==p4_identity
            print(json.dumps(dict(result='PASS',negative_case='ACTUAL_100000x200_EXPANDED_TEXT',
                rows=100000,columns=200,P4_internal_bytes=p4_identity[0],P4_internal_unchanged=True,
                error=error.code,Order=scenario.order().status,new_final_artifacts=0,new_qa_reports=0,
                safe_preallocation_rejection=True,elapsed_seconds=monotonic()-started),indent=2))
            return
        elapsed=monotonic()-started
    finally:
        stop.set();thread.join();peak[0]=max(peak[0],current_rss())
    assert peak[0]-baseline<=536870912
    assert decision.order_status=='READY' and decision.report['overall_status']=='PASS'
    output=scenario.env.workspace.path(decision.artifact.workspace_relpath)
    headers=['id']+[f'c{i:03d}' for i in range(1,200)]
    count=cells=0
    if a.format=='CSV':
        with output.open(encoding='utf-8',newline='') as f:
            reader=csv.reader(f,strict=True);assert next(reader)==headers
            for count,row in enumerate(reader,1):
                assert row==[f'{count:06d}']+['x']*199
                cells+=len(row)
        assert hashlib.sha256(output.read_bytes()).hexdigest()==identity['sha256']
    else:
        binary=output.open('rb')
        book=load_workbook(binary,read_only=True,data_only=False,keep_links=False)
        try:
            assert book.sheetnames==['Data'];reader=iter(book['Data'].rows)
            assert [c.value for c in next(reader)]==headers
            for count,row in enumerate(reader,1):
                assert [c.value for c in row]==[f'{count:06d}']+['x']*199
                assert all(c.data_type=='s' for c in row)
                cells+=len(row)
        finally:book.close();binary.close()
    assert count==100000 and cells==20000000
    assert scenario.delta()==dict(artifacts=1,qa_reports=1,event_log=2,approvals=0,execution_runs=0)
    assert scenario.env.workspace.inspect(internal.workspace_relpath)==p4_identity
    with scenario.uow() as u:assert u.runs.get(scenario.run_id)==run_before
    assert bootstrap(Config(scenario.env.workspace.root)).health=='ready'
    print(json.dumps(dict(result='PASS',tested_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                         tested_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
                         format=a.format,source_type='LOCAL_CSV',generator_command=generator,generator=identity,
                         rows=count,columns=200,independent_cells_checked=cells,
                         baseline_rss_bytes=baseline,peak_rss_bytes=peak[0],incremental_peak_rss_bytes=peak[0]-baseline,
                         rss_sample_count=samples[0],rss_sampling_interval_seconds=0.005,
                         P5_elapsed_seconds=elapsed,runtime_resources=decision.resources,
                         Order=decision.order_status,QA=decision.report['overall_status'],
                         final_artifacts=1,qa_reports=1,P4_internal_unchanged=True,
                         export_identity=decision.report['dataset_summary'],isolated_test_approvals_only=True),indent=2))


if __name__=='__main__':main()
