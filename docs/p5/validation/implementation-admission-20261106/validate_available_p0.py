"""Validate real available P0 objects; explicitly report missing originals."""
import argparse
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


def main(root,out,supplement):
    schemas={p.name:json.loads(p.read_text()) for p in (root/'contracts').rglob('*.schema.json')}
    registry=Registry().with_resources((s['$id'],Resource.from_contents(s)) for s in schemas.values())
    validators={n:Draft202012Validator(s,registry=registry,format_checker=FormatChecker()) for n,s in schemas.items()}
    for s in schemas.values():
        Draft202012Validator.check_schema(s)
    cases=[]
    def valid(path,schema,subdocument=None):
        doc=json.loads(path.read_text()) if subdocument is None else subdocument
        validators[schema+'.schema.json'].validate(doc)
        cases.append({'path':str(path),'schema':schema,'outcome':'PASS'})
    for directory in sorted((root/'fixtures').iterdir()):
        if not directory.is_dir():
            continue
        for filename,schema in [('brief_version.json','brief_version'),('transformation_spec_version.json','transformation_spec_version'),('expected_qa_report.json','qa_report')]:
            path=directory/filename
            if path.exists():
                valid(path,schema)
                document=json.loads(path.read_text())
                if schema=='transformation_spec_version':
                    for op in document['pipeline']:
                        valid(path,op['type'],op)
                if schema=='qa_report':
                    for check in document['deterministic_checks']:
                        valid(path,'qa_check_result',check)
        for path in sorted((directory/'approvals').glob('*.json')):
            valid(path,'approval')
        path=directory/'acceptance_criteria.json'
        if path.exists():
            for criterion in json.loads(path.read_text()):
                valid(path,'acceptance_criterion',criterion)
    negative=[]
    for path in sorted((root/'fixtures').glob('*/invalid_examples/*.json')):
        name=path.name
        payload=json.loads(path.read_text())
        schema = ('approval' if 'target_version_id' in payload else
                  'transformation_spec_version' if 'pipeline' in payload else
                  'brief_version' if 'fields' in payload else 'operation')
        if 'operation_invalid_separators' in name:
            schema='parse_number'
        if 'sort_length_mismatch' in name:
            schema='sort'
        if 'unknown_operation' in name:
            schema='operation'
        errors=list(validators[schema+'.schema.json'].iter_errors(json.loads(path.read_text())))
        negative.append({'path':str(path.relative_to(root)), 'schema':schema,
                         'schema_outcome':'REJECTED' if errors else 'ACCEPTED_REQUIRES_SEMANTIC_GUARD',
                         'schema_errors':[e.message for e in errors]})
        if '.schema_invalid.' in name or 'output_name_with_tab' in name:
            assert errors, (path,'Known schema-invalid example was accepted')
    # Schema validity does not grant a real Approval to the synthetic supplement.
    for filename,schema in [('transformation_spec_version_v2_CANDIDATE.json','transformation_spec_version'),
                            ('transformation_approval_v2_TEST_ONLY.json','approval'),
                            ('qa_report_specimen_v2_TEST_ONLY.json','qa_report')]:
        valid(supplement/'fixtures/P-B_versioned'/filename,schema)
    manifest=json.loads((root/'PACK_MANIFEST.json').read_text())
    present,missing=[],[]
    for entry in manifest['files']:
        path=root/entry['path']
        if not path.is_file():
            missing.append(entry['path'])
            continue
        raw=path.read_bytes()
        assert len(raw)==entry['size_bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'],path
        present.append(entry['path'])
    assert len(missing)==13 and all(p.startswith('fixtures/P-C_approval_safety/') for p in missing)
    report={'schemas_checked':len(schemas),'positive_validations':len(cases),'positive_schema_results':cases,
            'negative_examples_inspected':len(negative),'negative_schema_results':negative,
            'manifest_present_matches':len(present),'manifest_declared_count':len(manifest['files']),
            'missing_P_C_originals':missing,
            'available_schema_validation':'PASS','complete_original_P0_pack':'INCOMPLETE_13_MISSING_ORIGINALS',
            'P_C_full_positive':'BLOCKED_NOT_CLAIMED',
            'synthetic_supplement_approval':'SCHEMA_VALID_TEST_ONLY_NOT_BUSINESS_AUTHORITY'}
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('positive_schema_results','negative_schema_results')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--p0-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--supplement',type=Path,required=True)
    a=p.parse_args();main(a.p0_root,a.out,a.supplement)
