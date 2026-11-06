"""P0-schema report mapping from computed checks and verified final bytes."""
from uuid import uuid4
from vde.contracts import validate
from vde.errors import utc_now
from .qa import IDS, CONDITIONAL
from .errors import require


def overall(checks):
    if any(c['status']=='FAIL' and c['severity'] in ('BLOCKER','ERROR') for c in checks):
        return 'FAIL'
    if any(c['status'] in ('WARN','FAIL') for c in checks):
        return 'PASS_WITH_WARNINGS'
    return 'PASS'


def build(context, artifact, export, checks):
    require(set(c['check_id'] for c in checks) == set(IDS) and
            all(c['check_id'] in CONDITIONAL for c in checks if c['status']=='SKIPPED'),
            'SCHEMA_MISMATCH', 'Mandatory deterministic QA coverage is incomplete')
    blocking = list(dict.fromkeys(c['check_id'] for c in checks
                                 if c['status']=='FAIL' and c['severity'] in ('BLOCKER','ERROR')))
    warnings = list(dict.fromkeys(c['check_id'] for c in checks if c['status']=='WARN' or
                                  c['status']=='FAIL' and c['severity'] not in ('BLOCKER','ERROR')))
    if any(c['check_id']=='DQ-023' and c['status']=='WARN' for c in checks):
        warnings.append('XLSX_FORMULA_PRESENT')
    doc = dict(schema_version='1.1',report_id='p5-qa-'+str(uuid4()),run_id=context.run.id,
               brief_version_id=context.brief.id,transformation_spec_version_id=context.spec.id,
               generated_at=utc_now(),overall_status=overall(checks),
               dataset_summary=dict(dataset_id=context.projection.output['dataset_id'],
                                    row_count=export['rows'],column_count=export['columns'],
                                    columns=list(context.projection.columns),output_headers=export['headers'],
                                    file_size_bytes=export['size'],checksum=export['checksum']),
               deterministic_checks=checks,llm_review=dict(status='NOT_APPLICABLE',reason='PILOT_SLICE_V1_NO_LLM'),
               blocking_issues=blocking,warnings=warnings,sampling_manifest=None,
               known_limitations=[
                   'Pilot Slice V1: deterministic checks only; no LLM review.',
                   'CSV lexical projection cannot distinguish a typed null from empty text; typed QA uses P4 originals.',
                   'Source XLSX formulas use previously cached values only; no recalculation.',
                   'Resource protection uses sampled RSS; arbitrary maximum-length data may fail closed.',
                   'Local single-process serialization is not distributed locking; no P6 delivery is performed.'],
               artifacts=[dict(artifact_type=artifact.artifact_type,path=artifact.workspace_relpath,checksum=artifact.checksum)])
    validate(doc,'qa_report')
    return doc
