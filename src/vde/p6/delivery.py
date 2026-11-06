"""Read-only, verified terminal delivery and bounded immutable snapshots.

The browser transfers prepared bytes.  Preparing and subsequent UI renders
verify current persisted context; a download click is not a disk-read hook.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
from threading import Event, Lock, Thread
from time import monotonic
import unicodedata

from jsonschema.exceptions import ValidationError

from vde.contracts import validate
from vde.errors import StorageError
from vde.ingestion.limits import current_rss
from vde.p5.errors import P5Error
from vde.p5.service import P5Service
from vde.persistence.uow import UnitOfWork
from vde.recovery import recover


RSS_LIMIT = 536870912
RESERVE_BYTES = 64 * 1024 * 1024
_LOG = logging.getLogger(__name__)
_MIMES = {
    'CSV': 'text/csv',
    'XLSX': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


class P6Error(Exception):
    """UI-only diagnostic; these codes are never P0 ExecutionErrors."""

    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(reason)

    def public(self):
        return dict(code=self.code, message='The requested P6 action is unavailable.',
                    details={'reason': self.reason[:1000]})


def _require(condition, code='P6_INTEGRITY_FAILED', reason='Delivery context is inconsistent.'):
    if not condition:
        raise P6Error(code, reason)


def _json_bytes(document):
    # This exact serialization is the P6-C04 contract, not P0 canonical hashing.
    try:
        return json.dumps(document, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(',', ':')).encode('utf-8')
    except (ValueError, TypeError, UnicodeError) as exc:
        raise P6Error('P6_INTEGRITY_FAILED', 'Persisted delivery JSON is invalid.') from exc


def _rss(reader):
    try:
        return reader()
    except (OSError, RuntimeError, ValueError) as exc:
        raise P6Error('STORAGE_ERROR', 'Linux memory measurement is unavailable.') from exc


class Budget:
    """Sample actual Linux RSS across preparation and download-button binding.

    A supplied reader can add a deterministic restriction for tests.  It never
    replaces the real RSS reader or increases the approved 512 MiB envelope.
    Sampling is evidence, not OS memory isolation.
    """

    def __init__(self, limit=RSS_LIMIT, rss_reader=None):
        self.limit = min(limit, RSS_LIMIT)
        self.reader = current_rss
        self.baseline = self.peak = _rss(self.reader)
        self.extra_reader = rss_reader
        self.extra_baseline = self.extra_peak = _rss(rss_reader) if rss_reader else None
        self.started = monotonic()
        self.samples = 0
        self.sampling_interval = 0.01
        self.stopped = Event()
        self.monitor = None
        self.lock = Lock()
        self.failure = None
        self.characteristics = {}
        self.resources = {}

    def _sample(self):
        # Measurement failures must reach the caller; a failed daemon must not
        # silently turn memory enforcement off.
        while not self.stopped.wait(self.sampling_interval):
            try:
                self._observe()
            except P6Error as exc:
                self.failure = exc
                self.stopped.set()

    def _observe(self):
        rss = _rss(self.reader)
        extra = _rss(self.extra_reader) if self.extra_reader else None
        with self.lock:
            self.peak = max(self.peak, rss)
            if extra is not None:
                self.extra_peak = max(self.extra_peak, extra)
            self.samples += 1
        return rss, extra

    def _summary(self):
        return dict(baseline_rss=self.baseline, peak_rss=self.peak,
                    incremental_peak_rss=max(0, self.peak - self.baseline),
                    rss_limit=self.limit, rss_samples=self.samples,
                    sampling_interval_seconds=self.sampling_interval,
                    elapsed_seconds=monotonic() - self.started,
                    **self.characteristics)

    def summary(self):
        self.resources.update(self._summary())
        return dict(self.resources)

    def check(self, allocation=0):
        if self.failure is not None:
            raise P6Error('STORAGE_ERROR', 'Linux memory measurement is unavailable.') from self.failure
        rss, extra = self._observe()
        exceeded = (self.peak - self.baseline > self.limit or
                    max(0, rss - self.baseline) + allocation > self.limit)
        if extra is not None:
            exceeded |= (self.extra_peak - self.extra_baseline > self.limit or
                         max(0, extra - self.extra_baseline) + allocation > self.limit)
        self.summary()
        if exceeded:
            _LOG.warning('P6_DOWNLOAD_RESOURCE_LIMIT limit=%s result_size=%s report_size=%s '
                         'estimate=%s incremental_peak=%s', self.limit,
                         self.characteristics.get('result_size_bytes'),
                         self.characteristics.get('report_size_bytes'),
                         self.characteristics.get('estimated_allocation_bytes'),
                         max(0, self.peak - self.baseline))
            raise P6Error('P6_DOWNLOAD_RESOURCE_LIMIT', 'Verified download exceeds the memory budget.')

    def preflight(self, result_size, report_size):
        estimate = 3 * result_size + report_size + RESERVE_BYTES
        self.characteristics.update(result_size_bytes=result_size, report_size_bytes=report_size,
                                    estimated_allocation_bytes=estimate)
        # Frozen P5 read_decision hashes the internal Artifact incrementally;
        # it does not invoke complete()/read_internal or materialize that file.
        # The same RSS baseline still covers the entire verification call.
        self.check(allocation=estimate)

    @contextmanager
    def binding(self):
        """Retain the original baseline while Streamlit binds both buffers."""
        self.check()
        if self.monitor is not None:
            raise RuntimeError('Nested P6 memory monitoring is not supported')
        self.stopped.clear()
        self.monitor = Thread(target=self._sample, name='p6-rss', daemon=True)
        self.monitor.start()
        try:
            yield self
            self.check()
        except MemoryError as exc:
            _LOG.warning('P6_DOWNLOAD_RESOURCE_LIMIT download buffer allocation failed')
            raise P6Error('P6_DOWNLOAD_RESOURCE_LIMIT', 'Verified download allocation failed.') from exc
        finally:
            self.stopped.set()
            self.monitor.join()
            self.monitor = None
            self._observe()
            self.summary()
        self.check()

    def __enter__(self):
        self._active_binding = self.binding()
        return self._active_binding.__enter__()

    def __exit__(self, *args):
        return self._active_binding.__exit__(*args)


@dataclass(frozen=True)
class DeliveryView:
    order: object
    run: object
    decision: object
    spec: object
    brief: object
    approvals: tuple
    report_record: object
    result_name: str
    result_mime: str
    report_name: str
    report_mime: str
    _context_key: str = field(repr=False)

    @property
    def artifact(self):
        return self.decision.artifact

    @property
    def report(self):
        return self.decision.report

    @property
    def diagnostic(self):
        return self.order.status == 'NEEDS_FIX'

    @property
    def key(self):
        return (self.order.id, self.run.id, self.artifact.id, self.artifact.checksum,
                self.report['overall_status'], self.artifact.format)

    @property
    def context_key(self):
        return self._context_key


@dataclass(frozen=True)
class Snapshot:
    key: tuple
    result_bytes: bytes
    report_bytes: bytes
    result_name: str
    result_mime: str
    report_name: str
    report_mime: str
    resources: dict
    view: DeliveryView
    guard: Budget = field(repr=False, compare=False)

    @property
    def context_key(self):
        return self.view.context_key


@dataclass(frozen=True)
class _Context:
    order: object
    run: object
    brief: object
    spec: object
    approvals: tuple
    reports: tuple
    artifacts: tuple


def _result_name(file_name, format, diagnostic):
    _require(format in _MIMES and isinstance(file_name, str) and file_name,
             reason='The approved output format or name is invalid.')
    _require(not any(c in '/\\<>:"|?*' or unicodedata.category(c).startswith('C') for c in file_name)
             and file_name not in ('.', '..') and not file_name.startswith('.')
             and file_name == file_name.strip() and not file_name.endswith('.'),
             reason='The approved output filename is unsafe.')
    extension = '.' + format.lower()
    _require(file_name.lower().endswith(extension) and len(file_name) > len(extension),
             reason='The approved output filename has the wrong extension.')
    stem = file_name[:-len(extension)]
    return stem + ('_DIAGNOSTIC_NOT_FOR_DELIVERY' if diagnostic else '') + extension


class DeliveryService:
    def __init__(self, env, *, p5_service=None, budget_factory=None):
        self.env = env
        self.p5 = p5_service if p5_service is not None else P5Service(env)
        # An optional factory adds stricter admission; actual RSS is mandatory.
        self.budget_factory = budget_factory

    def _uow(self):
        return UnitOfWork(self.env.database, self.env.workspace)

    def _owned(self, order_id, run_id):
        _require(isinstance(order_id, str) and order_id and isinstance(run_id, str) and run_id,
                 'P6_NOT_READY', 'Select an existing Order and Run.')
        with self._uow() as uow:
            # Establish ownership before recovery, P5 or artifact APIs.  The
            # nonthrowing queries also keep missing IDs a generic UI diagnostic.
            exists = uow.connection.execute('SELECT id FROM orders WHERE id=?', (order_id,)).fetchone()
            row = uow.connection.execute('SELECT order_id FROM execution_runs WHERE id=?', (run_id,)).fetchone()
            _require(exists is not None and row is not None, 'P6_NOT_READY',
                     'The selected Order or Run is unavailable.')
            _require(row['order_id'] == order_id, 'P6_CROSS_ORDER',
                     'The selected Run does not belong to the selected Order.')
            return uow.orders.get(order_id), uow.runs.get(run_id)

    def _health(self):
        report = recover(self.env.database, self.env.workspace)
        _require(report.health != 'blocked', 'STORAGE_ERROR',
                 'Local storage is blocked; inspect recovery diagnostics.')
        _require(report.health == 'ready', 'P6_NOT_READY',
                 'Local storage recovery must be ready before download.')

    def _context(self, order_id, run_id):
        # Repeat ownership before loading any linked report or Artifact record.
        order, run = self._owned(order_id, run_id)
        with self._uow() as uow:
            fresh_order, fresh_run = uow.orders.get(order_id), uow.runs.get(run_id)
            _require((fresh_order, fresh_run) == (order, run) and fresh_run.order_id == order_id)
            return _Context(fresh_order, fresh_run, uow.briefs.get(run.brief_version_id),
                            uow.specs.get(run.transformation_spec_version_id),
                            (uow.approvals.get(run.brief_approval_id),
                             uow.approvals.get(run.transformation_approval_id)),
                            tuple(uow.reports.list_for_run(run_id)),
                            tuple(uow.artifacts.list_for_run(run_id)))

    def _preflight(self, context, budget):
        _require(len(context.reports) == 1, 'P6_NOT_READY', 'The terminal QAReport is unavailable.')
        report = context.reports[0].report_json
        validate(report, 'qa_report')
        report_bytes = _json_bytes(report)
        final = [a for a in context.artifacts if a.artifact_type in ('RESULT_CSV', 'RESULT_XLSX')]
        internal = [a for a in context.artifacts if a.artifact_type == 'P4_INTERNAL']
        _require(len(final) == len(internal) == 1 and len(context.artifacts) == 2)
        size, checksum = self.env.workspace.inspect(final[0].workspace_relpath)
        _require(checksum == final[0].checksum and
                 (size, checksum) == (report['dataset_summary']['file_size_bytes'],
                                      report['dataset_summary']['checksum']))
        budget.preflight(size, len(report_bytes))
        return report_bytes

    def _read_view(self, order_id, run_id, budget=None):
        initial = self._owned(order_id, run_id)
        self._health()
        _require(initial[0].status in ('READY', 'NEEDS_FIX') and initial[1].status == 'succeeded',
                 'P6_NOT_READY', 'A terminal verified P5 decision is required.')
        context = self._context(order_id, run_id)
        _require((context.order, context.run) == initial)
        _require(len(context.reports) == 1, 'P6_NOT_READY', 'The terminal QAReport is unavailable.')
        report_bytes = self._preflight(context, budget) if budget is not None else None
        try:
            decision = self.p5.read_decision(run_id)
        except P5Error as exc:
            code = ('P6_NOT_READY' if exc.code == 'STATE_INVALID_TRANSITION' else
                    'P6_DOWNLOAD_RESOURCE_LIMIT' if exc.code == 'EXPORT_FAILED' else
                    'P6_INTEGRITY_FAILED')
            raise P6Error(code, 'The persisted P5 decision could not be verified.') from exc
        except (ValidationError, KeyError, TypeError, ValueError) as exc:
            # Frozen admission reads persisted JSON; malformed shapes/numbers
            # are expected corruption cases. Unknown exception types propagate.
            raise P6Error('P6_INTEGRITY_FAILED', 'Persisted P5 context is malformed.') from exc
        fresh = self._context(order_id, run_id)
        _require(fresh == context, reason='Delivery context changed during verification.')
        _require(len(context.reports) == 1, 'P6_NOT_READY', 'The terminal QAReport is unavailable.')
        record, artifact, report = context.reports[0], decision.artifact, decision.report
        validate(report, 'qa_report')
        output = context.spec.document_json['output']
        _require((decision.run_id, decision.order_status) == (run_id, context.order.status)
                 and report == record.report_json
                 and (report['report_id'], report['run_id'], report['brief_version_id'],
                      report['transformation_spec_version_id']) ==
                     (record.report_id, run_id, context.brief.id, context.spec.id)
                 and artifact is not None and artifact in context.artifacts
                 and artifact.run_id == run_id
                 and artifact.format == output['format'] and artifact.format in _MIMES
                 and artifact.artifact_type == 'RESULT_' + artifact.format
                 and report['artifacts'] == [dict(artifact_type=artifact.artifact_type,
                                                 path=artifact.workspace_relpath, checksum=artifact.checksum)]
                 and report['dataset_summary']['checksum'] == artifact.checksum)
        overall = report['overall_status']
        _require((context.order.status == 'READY' and overall in ('PASS', 'PASS_WITH_WARNINGS')
                  and not report['blocking_issues']) or
                 (context.order.status == 'NEEDS_FIX' and overall == 'FAIL' and report['blocking_issues']))
        result_name = _result_name(output['file_name'], artifact.format, context.order.status == 'NEEDS_FIX')
        controlled_id = self.env.workspace.identifier(record.report_id)
        context_key = hashlib.sha256(_json_bytes(asdict(context))).hexdigest()
        view = DeliveryView(context.order, context.run, decision, context.spec, context.brief,
                            context.approvals, record, result_name, _MIMES[artifact.format],
                            'qa_report_' + controlled_id + '.json', 'application/json; charset=utf-8', context_key)
        if budget is not None:
            budget.check()
        return view, report_bytes

    def view(self, order_id, run_id):
        try:
            return self._read_view(order_id, run_id)[0]
        except StorageError as exc:
            raise P6Error('STORAGE_ERROR', 'Local storage could not be verified.') from exc
        except ValidationError as exc:
            raise P6Error('P6_INTEGRITY_FAILED', 'Persisted delivery documents are invalid.') from exc

    def prepare(self, order_id, run_id):
        """Return one result bytes object and one exact report bytes object.

        The UI must clear its previous snapshot before calling and must bind
        both buttons within ``snapshot.guard.binding()`` before retaining it.
        """
        try:
            budget = Budget()
            with budget.binding():
                extra = self.budget_factory() if self.budget_factory is not None else None
                with _extra_budget(extra):
                    view, report_bytes = self._read_view(order_id, run_id, budget)
                    artifact, summary = view.artifact, view.report['dataset_summary']
                    size, checksum = self.env.workspace.inspect(artifact.workspace_relpath)
                    _require((size, checksum) == (summary['file_size_bytes'], artifact.checksum)
                             and checksum == summary['checksum'])
                    budget.preflight(size, len(report_bytes))
                    if extra is not None:
                        extra.check(allocation=3 * size + len(report_bytes) + RESERVE_BYTES)
                    data = self.env.workspace.read_verified(artifact.workspace_relpath, artifact.checksum, size)
                    _require(isinstance(data, bytes) and len(data) == size and
                             hashlib.sha256(data).hexdigest() == summary['checksum'])
                    budget.check()
                    # No second full bytes snapshot or repeated QA serialization.
                    # Verify the context and health afresh before authorizing it.
                    self._owned(order_id, run_id)
                    self._health()
                    fresh = self._context(order_id, run_id)
                    _require(hashlib.sha256(_json_bytes(asdict(fresh))).hexdigest() == view.context_key,
                             reason='Delivery context changed during preparation.')
                    if extra is not None:
                        extra.check()
                    budget.check()
                    snapshot = Snapshot(view.key, data, report_bytes, view.result_name, view.result_mime,
                                        view.report_name, view.report_mime, budget.resources, view, budget)
            budget.check()
            return snapshot
        except MemoryError as exc:
            _LOG.warning('P6_DOWNLOAD_RESOURCE_LIMIT allocation failed')
            raise P6Error('P6_DOWNLOAD_RESOURCE_LIMIT', 'Verified download allocation failed.') from exc
        except StorageError as exc:
            raise P6Error('STORAGE_ERROR', 'Local storage could not be verified.') from exc
        except ValidationError as exc:
            raise P6Error('P6_INTEGRITY_FAILED', 'Persisted delivery documents are invalid.') from exc

    def verify_snapshot(self, snapshot, order_id, run_id):
        """Fresh rerender guard; failures require the UI to clear both buffers."""
        _require(isinstance(snapshot, Snapshot) and snapshot.key[:2] == (order_id, run_id),
                 'P6_NOT_READY', 'Prepare a snapshot for the selected Order and Run.')
        view = self.view(order_id, run_id)
        _require(view.key == snapshot.key and view.context_key == snapshot.context_key,
                 reason='The prepared delivery context changed.')
        snapshot.guard.check()
        return view


@contextmanager
def _extra_budget(budget):
    """Test admission can only tighten the mandatory actual-RSS budget."""
    if budget is None:
        yield
    else:
        with budget:
            yield
