"""P0 document validation only. No dataset execution or P4 preflight."""
from copy import deepcopy
import unicodedata
from jsonschema.exceptions import ValidationError
from vde.contracts import validate, content_hash, nfc
from .errors import require, WorkflowError

OPERATIONS = frozenset(('rename', 'select_columns', 'drop_columns', 'trim', 'change_case',
                       'replace', 'parse_number', 'parse_date', 'fill_missing',
                       'drop_missing', 'deduplicate', 'sort'))


def _prepare(document, kind):
    code = 'VALIDATION_BRIEF_SCHEMA' if kind == 'brief_version' else 'VALIDATION_TRANSFORMATION_SCHEMA'
    try:
        doc = deepcopy(document)
        fields_key = 'fields' if kind == 'brief_version' else 'expected_schema'
        for field in doc.get(fields_key, []):
            value = field.get('output_name', field['name'])
            if isinstance(value, str):
                field['output_name'] = unicodedata.normalize('NFC', value.strip())
        # Schema validation still covers every top-level, nested and identity field.
        validate(doc, kind)
        names = [f['name'] for f in doc[fields_key]]
        headers = [f['output_name'] for f in doc[fields_key]]
        require(len(set(names)) == len(names) and len(set(headers)) == len(headers), code,
                'Field identifiers and normalized output headers must be unique')
        output = doc['output_contract' if kind == 'brief_version' else 'output']
        require(set(output['column_order']) == set(names), code,
                'Output order must contain each internal field identifier exactly once')
        # Hash strings/keys are NFC-normalized by the frozen P1 hash implementation.
        # Check key collisions even outside the semantic hash payload.
        nfc(doc)
        doc['content_hash'] = content_hash(doc, kind)
        validate(doc, kind)
        return doc
    except ValidationError as exc:
        if kind == 'brief_version' and list(exc.absolute_path)[:1] == ['acceptance_criteria']:
            code = 'VALIDATION_ACCEPTANCE_CRITERION'
        raise WorkflowError(code, 'Schema violation at /' + '/'.join(map(str, exc.absolute_path))) from exc
    except (TypeError, KeyError, ValueError, AttributeError, OverflowError) as exc:
        raise WorkflowError(code, 'Invalid JSON document or normalization') from exc


def validate_brief(document, order, asset):
    doc = _prepare(document, 'brief_version')
    require(doc['order_id'] == order.id, 'VERSION_INCOMPATIBLE', 'Brief belongs to another Order')
    source = doc['inputs_expected'][0]
    require(source['asset_id'] == asset.id and asset.order_id == order.id,
            'INPUT_NOT_FOUND', 'Brief source is not the selected Order-owned asset')
    require(doc['source_refs'] == [asset.id], 'INPUT_NOT_FOUND', 'Exactly one selected source reference is required')
    criteria = doc['acceptance_criteria']
    ids = [c['criterion_id'] for c in criteria]
    require(len(set(ids)) == len(ids), 'VALIDATION_ACCEPTANCE_CRITERION', 'Duplicate criterion ID')
    names = {f['name'] for f in doc['fields']}
    for criterion in criteria:
        validate(criterion, 'acceptance_criterion')
        target = criterion['target']
        refs = ([target['column']] if target['column'] else []) + (target['columns'] or [])
        require(set(refs) <= names, 'VALIDATION_ACCEPTANCE_CRITERION', 'Criterion refers to an unknown field')
    volume = doc['volume_expectation']
    require(volume['mode'] != 'RANGE' or volume['min_count'] <= volume['max_count'],
            'VALIDATION_BRIEF_SCHEMA', 'Invalid volume range')
    require(set(doc['data_quality_expectations']['duplicate_key'] or []) <= names,
            'VALIDATION_BRIEF_SCHEMA', 'Duplicate key refers to an unknown field')
    return doc


def validate_spec(document, order, approved_brief, selection):
    # Classify the closed-operation negatives before the union schema's generic error.
    if isinstance(document, dict) and isinstance(document.get('pipeline'), list):
        for op in document['pipeline']:
            if isinstance(op, dict):
                require(op.get('type') in OPERATIONS, 'INVALID_OPERATION', 'Operation is outside the Pilot whitelist')
                try:
                    validate(op, op['type'])
                except ValidationError as exc:
                    raise WorkflowError('INVALID_PARAMETER', 'Invalid closed operation parameters') from exc
    doc = _prepare(document, 'transformation_spec_version')
    brief, approval = approved_brief
    require(approval is not None, 'APPROVAL_MISSING', 'Selected Brief approval is required')
    require((approval.order_id, approval.target_type, approval.target_version_id,
             approval.target_content_hash, approval.context_brief_version_id,
             approval.context_brief_content_hash) ==
            (order.id, 'BRIEF', brief.id, brief.content_hash, None, None),
            'VERSION_INCOMPATIBLE', 'Brief approval does not match exact order/version/hash/context')
    require((doc['order_id'], doc['brief_version_id'], doc['brief_content_hash']) ==
            (order.id, brief.id, brief.content_hash), 'VERSION_INCOMPATIBLE', 'Spec exact Brief context differs')
    source = doc['inputs'][0]
    require(source['asset_id'] == selection.asset_id and selection.order_id == order.id and
            source['asset_id'] == brief.document_json['inputs_expected'][0]['asset_id'],
            'INPUT_NOT_FOUND', 'Spec source differs from the selected Brief asset')
    require(source['source_type'] == selection.source_type and
            {k: source[k] for k in ('sheet_name', 'csv_options')} == selection.selection,
            'VALIDATION_TRANSFORMATION_SCHEMA', 'Spec options differ from explicit P2 preview selection')
    expected_input = brief.document_json['inputs_expected'][0]
    require((source['source_type'], source['sheet_name']) ==
            (expected_input['input_type'], expected_input['sheet_name']),
            'VALIDATION_TRANSFORMATION_SCHEMA', 'Spec source selection differs from Brief expected input')
    require(set(doc['acceptance_criteria_ref']) <= {c['criterion_id'] for c in brief.document_json['acceptance_criteria']},
            'VALIDATION_TRANSFORMATION_SCHEMA', 'Spec criterion references must exist in the selected Brief')
    ids = [op['operation_id'] for op in doc['pipeline']]
    require(len(set(ids)) == len(ids), 'VALIDATION_TRANSFORMATION_SCHEMA', 'Duplicate operation ID')
    # Describe a single linear dataset chain without inspecting/transmuting any data.
    current = source['dataset_id']
    datasets = {current}
    for op in doc['pipeline']:
        require(op['input_dataset'] == current and op['output_dataset'] not in datasets,
                'VALIDATION_TRANSFORMATION_SCHEMA', 'Invalid single-dataset pipeline references')
        current = op['output_dataset']
        datasets.add(current)
        if op['type'] == 'sort':
            require(len(op['params']['by']) == len(op['params']['ascending']),
                    'INVALID_PARAMETER', 'Sort direction count differs from columns')
        if op['type'] == 'parse_number':
            require(op['params']['decimal_separator'] != op['params']['thousands_separator'],
                    'INVALID_PARAMETER', 'Number separators must differ')
    require(current == doc['output']['dataset_id'], 'VALIDATION_TRANSFORMATION_SCHEMA', 'Output dataset is not final pipeline result')
    return doc
