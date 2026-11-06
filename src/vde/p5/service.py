"""Explicit export/QA, two existing P1 commit boundaries, detect-only retry."""
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import tempfile
from threading import Lock
from uuid import uuid4
from vde.errors import StorageError, utc_now
from vde.execution.errors import ExecutionError
from vde.models import QAReportRecord, EventRecord
from vde.persistence.uow import UnitOfWork
from vde.storage import Storage
from .budget import Budget
from .contract import admit, health, read_internal, rows
from .errors import P5Error, require
from . import export as writer
from . import roundtrip
from .qa import Facts, evaluate_all
from .report import build, overall

_LOCKS = tuple(Lock() for _ in range(64))


def artifact_id(run_id, format):
    return 'p5-final-'+hashlib.sha256((run_id+'\0'+format).encode('utf-8')).hexdigest()


def _run_lock(env,run_id):
    slot=int(hashlib.sha256((str(env.database)+'\0'+run_id).encode()).hexdigest()[:8],16)%len(_LOCKS)
    return _LOCKS[slot]


@dataclass(frozen=True)
class P5Decision:
    run_id: str
    order_status: str
    report: dict
    artifact: object
    resources: dict
    repeated: bool = False
    error_json: dict | None = None


class P5Service:
    def __init__(self, env, *, checkpoint=None, budget_factory=Budget):
        self.env = env
        self.checkpoint = checkpoint or (lambda stage: None)
        self.budget_factory = budget_factory

    def _uow(self):
        return UnitOfWork(self.env.database,self.env.workspace)

    def inspect(self, run_id, expected_order=None):
        health(self.env)
        with self._uow() as uow:
            return admit(uow,self.env,run_id,expected_order)

    def read_decision(self,run_id):
        """Verified terminal view. No P4 read_result or business writes."""
        with _run_lock(self.env,run_id),self.budget_factory() as budget:
            context=self.inspect(run_id)
            require(context.order.status in ('READY','NEEDS_FIX'),'STATE_INVALID_TRANSITION','P5 decision is not terminal')
            return self._terminal(context,self._final(context),budget)

    def _final(self, context):
        final = [a for a in context.artifacts if a != context.internal]
        require(len(final)<=1 and all(a.artifact_type == 'RESULT_'+context.projection.output['format']
                and a.format == context.projection.output['format']
                and a.id == artifact_id(context.run.id,a.format) for a in final),
                'STORAGE_ERROR', 'Ambiguous or unauthorized final Artifact')
        return final[0] if final else None

    def _terminal(self, context, artifact, budget):
        require(artifact is not None and len(context.reports)==1, 'STORAGE_ERROR', 'Incomplete terminal P5 state')
        report = context.reports[0].report_json
        size, checksum = self.env.workspace.inspect(artifact.workspace_relpath)
        summary = report['dataset_summary']
        require(report['artifacts'] == [dict(artifact_type=artifact.artifact_type,path=artifact.workspace_relpath,checksum=artifact.checksum)]
                and (summary['file_size_bytes'],summary['checksum']) == (size,checksum)
                and checksum == artifact.checksum
                and summary['columns'] == list(context.projection.columns)
                and summary['output_headers'] == list(context.projection.headers)
                and summary['column_count'] == len(context.projection.columns)
                and summary['row_count'] == context.run.metrics_json['row_count']
                and report['overall_status'] == overall(report['deterministic_checks'])
                and context.order.status == ('NEEDS_FIX' if report['overall_status']=='FAIL' else 'READY'),
                'STORAGE_ERROR', 'Terminal report, Artifact and Order contradict')
        from .qa import IDS, CONDITIONAL
        checks = report['deterministic_checks']
        approved = {c['criterion_id'] for c in context.brief.document_json['acceptance_criteria']}
        approved &= set(context.spec.document_json['acceptance_criteria_ref'])
        expected_criteria={c['criterion_id']:c for c in context.brief.document_json['acceptance_criteria']
                           if c['criterion_id'] in approved and c['requirement_status']!='NOT_APPLICABLE'}
        from .qa import criterion_dq,json_value
        require(set(c['check_id'] for c in checks)==set(IDS) and
                len({(c['check_id'],c['criterion_id']) for c in checks})==len(checks) and
                all(c['criterion_id'] is None or c['criterion_id'] in approved for c in checks) and
                {c['criterion_id'] for c in checks if c['criterion_id']} == set(expected_criteria) and
                all(c['check_id'] in CONDITIONAL for c in checks if c['status']=='SKIPPED'),
                'STORAGE_ERROR', 'Terminal QA coverage differs')
        for check in checks:
            if check['criterion_id'] is not None:
                criterion=expected_criteria[check['criterion_id']]
                require(check['check_id']==criterion_dq(criterion) and check['expected']==json_value(criterion['expected']) and
                        check['severity']==criterion['severity'] and
                        check['target']['column']==criterion['target']['column'],
                        'STORAGE_ERROR','Terminal criterion binding differs')
        with self._uow() as uow:
            events=[e for e in uow.events.list_for_run(context.run.id) if e.event_type=='P5_QA_COMPLETED']
        require(len(events)==1 and events[0].payload_json['report_id']==report['report_id'] and
                events[0].payload_json['overall_status']==report['overall_status'],
                'STORAGE_ERROR','Terminal completion EventLog differs')
        budget.check()
        return P5Decision(context.run.id,context.order.status,report,artifact,budget.summary(),True,
                          events[0].payload_json.get('error'))

    def _fail(self, run_id, expected_order, exc, *, ordinary_storage=False):
        # A damaged workspace is read-only. Source/approval/admission errors do
        # not manufacture a new business decision. Final-UoW abort is retryable.
        if exc.code not in ('EXPORT_FAILED','ROUNDTRIP_MISMATCH','SCHEMA_MISMATCH','COLUMN_COLLISION') and not ordinary_storage:
            return
        try:
            health(self.env)
        except P5Error:
            return
        with self._uow() as uow:
            context = admit(uow,self.env,run_id,expected_order,projection_required=False)
            require(not context.reports and context.order.status=='EXECUTING',
                    'STATE_INVALID_TRANSITION','Failure context changed')
            public = exc.public(order_id=context.order.id,run_id=run_id)
            uow.orders.update(replace(context.order,status='FAILED',updated_at=utc_now()),expected=context.order)
            uow.events.append(EventRecord(str(uuid4()),context.order.id,'P5_FAILED',utc_now(),run_id,{'error':public}))

    def complete(self, run_id, expected_order):
        # Bounded striped locks avoid a growing global map of run identities.
        with _run_lock(self.env,run_id), self.budget_factory() as budget:
            final_transaction=False
            admitted=False
            try:
                context = self.inspect(run_id,expected_order)
                admitted=True
                artifact = self._final(context)
                if context.order.status in ('READY','NEEDS_FIX'):
                    return self._terminal(context,artifact,budget)
                require(not context.reports, 'STORAGE_ERROR','Report exists before terminal Order')
                self.checkpoint('after_admission')
                data = read_internal(self.env,context,budget)
                facts = Facts(context.projection,context.brief.document_json,context.spec.document_json,budget)
                if artifact is None:
                    with tempfile.TemporaryDirectory(prefix='p5-',dir=self.env.workspace.path('.staging')) as directory:
                        path = Path(directory)/('result.'+context.projection.output['format'].lower())
                        self.checkpoint('before_write')
                        writer.write(path,context.projection,rows(data,context),budget,facts.observe)
                        self.checkpoint('after_stage')
                        proof = roundtrip.verify(path,context.projection,rows(data,context),budget)
                        self.checkpoint('after_roundtrip')
                        require(proof['rows']==context.run.metrics_json['row_count'], 'SCHEMA_MISMATCH','Export count differs from P4')
                        checks = evaluate_all(context,facts,proof)
                        budget.check(allocation=proof['size'])
                        opaque = path.read_bytes()
                    # Scratch is gone before recovery inspects the workspace.
                    self.inspect(run_id,expected_order)
                    require(hashlib.sha256(opaque).hexdigest()==proof['checksum'] and len(opaque)==proof['size'],
                            'ROUNDTRIP_MISMATCH','Candidate changed before P1 publication')
                    artifact = Storage(self.env.database,self.env.workspace,
                        checkpoint=lambda stage:self.checkpoint('artifact_'+stage)).register_artifact(
                            id=artifact_id(run_id,context.projection.output['format']),run_id=run_id,
                            artifact_type='RESULT_'+context.projection.output['format'],
                            format=context.projection.output['format'],data=opaque)
                    del opaque
                    budget.check()
                    self.checkpoint('after_artifact_commit')
                else:
                    # Explicit retry reuses the committed object. No registration
                    # or orphan adoption occurs here.
                    for row in rows(data,context):
                        facts.observe(row)
                    proof = roundtrip.verify(self.env.workspace.path(artifact.workspace_relpath),
                                             context.projection,rows(data,context),budget)
                    checks = evaluate_all(context,facts,proof)
                del data
                health(self.env)
                require(self.env.workspace.inspect(artifact.workspace_relpath)==(proof['size'],proof['checksum'])
                        and artifact.checksum==proof['checksum'], 'STORAGE_ERROR','Published result differs')
                doc = build(context,artifact,proof,checks)
                public_error = P5Error('QA_BLOCKER','Deterministic blocking QA failed').public(
                    order_id=context.order.id,run_id=run_id) if doc['overall_status']=='FAIL' else None
                self.checkpoint('before_report_uow')
                final_transaction=True
                with self._uow() as uow:
                    fresh = admit(uow,self.env,run_id,expected_order)
                    require(not fresh.reports and self._final(fresh)==artifact,
                            'STORAGE_ERROR','Final report transaction context changed')
                    require(self.env.workspace.inspect(artifact.workspace_relpath)==(proof['size'],proof['checksum']),
                            'STORAGE_ERROR','Final result changed before report commit')
                    uow.reports.append(QAReportRecord.from_document(doc))
                    self.checkpoint('after_report_append')
                    status = 'NEEDS_FIX' if doc['overall_status']=='FAIL' else 'READY'
                    uow.orders.update(replace(fresh.order,status=status,updated_at=utc_now()),expected=fresh.order)
                    uow.events.append(EventRecord(str(uuid4()),fresh.order.id,'P5_QA_COMPLETED',utc_now(),run_id,
                                                  {'report_id':doc['report_id'],'overall_status':doc['overall_status'],
                                                   'error':public_error}))
                    self.checkpoint('before_report_commit')
                    budget.check()
                self.checkpoint('after_report_commit')
                return P5Decision(run_id,status,doc,artifact,budget.summary(),error_json=public_error)
            except P5Error as exc:
                self._fail(run_id,expected_order,exc)
                raise
            except ExecutionError as exc:
                raise P5Error(exc.code,exc.reason) from exc
            except StorageError as exc:
                error=P5Error('STORAGE_ERROR',exc.reason)
                if admitted and not final_transaction:
                    self._fail(run_id,expected_order,error,ordinary_storage=True)
                raise error from exc
            except OSError as exc:
                error = P5Error('EXPORT_FAILED','Export filesystem operation failed')
                self._fail(run_id,expected_order,error)
                raise error from exc
