"""Sampled Linux resource envelope; no changes to frozen P2 budgets."""
from time import monotonic

from vde.ingestion.limits import current_rss
from .errors import require


class Budget:
    def __init__(self, *, rss_limit=536870912, seconds=120, scratch_limit=2147483648,
                 rss_reader=current_rss, clock=monotonic):
        self.rss_reader, self.clock = rss_reader, clock
        self.baseline = rss_reader()
        self.started = clock()
        self.rss_limit, self.seconds, self.scratch_limit = rss_limit, seconds, scratch_limit
        self.peak = self.baseline
        self.scratch_bytes = self.scratch_peak = self.merge_fan_in = 0
        self.samples = 0
        self.io_since_check = 0

    def check(self):
        rss = self.rss_reader()
        self.peak = max(self.peak, rss)
        self.samples += 1
        require(rss - self.baseline <= self.rss_limit, 'STORAGE_ERROR', 'P4_RSS_BUDGET')
        require(self.clock() - self.started <= self.seconds, 'STORAGE_ERROR', 'P4_TIME_BUDGET')

    def shape(self, columns, count=0):
        require(0 < columns <= 200, 'SCHEMA_MISMATCH', 'P4_COLUMN_LIMIT', stage='PREFLIGHT')
        require(count <= 100000, 'SCHEMA_MISMATCH', 'P4_ROW_LIMIT', stage='PREFLIGHT')

    def reserve(self, size):
        require(self.scratch_bytes + size <= self.scratch_limit, 'STORAGE_ERROR', 'P4_SCRATCH_BUDGET')
        self.scratch_bytes += size
        self.scratch_peak = max(self.scratch_peak, self.scratch_bytes)

    def allocation(self, size):
        """Guard the known-size opaque payload required by frozen P1."""
        self.check()
        require(self.rss_reader()-self.baseline+size <= self.rss_limit,
                'STORAGE_ERROR', 'P4_RSS_BUDGET')

    def release(self, size):
        self.scratch_bytes -= size

    def write(self, stream, data):
        """Keep P4 scratch I/O and budget checkpoints within one MiB."""
        view, position = memoryview(data), 0
        while position < len(view):
            size = min(len(view)-position, 1048576-self.io_since_check)
            self.reserve(size)
            stream.write(view[position:position+size])
            position += size
            self.io_since_check += size
            if self.io_since_check == 1048576:
                self.check()
                self.io_since_check = 0

    def summary(self):
        return dict(incremental_peak_rss=self.peak-self.baseline,
                    elapsed_seconds=self.clock()-self.started, scratch_peak_bytes=self.scratch_peak,
                    merge_fan_in=self.merge_fan_in, rss_samples=self.samples)
