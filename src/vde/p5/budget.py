"""Sampled local RSS budget; a measured envelope, not process isolation."""
from threading import Event, Thread
from time import monotonic
from vde.ingestion.limits import current_rss
from .errors import require


class Budget:
    def __init__(self, limit=536870912, rss_reader=current_rss):
        self.limit, self.reader = limit, rss_reader
        self.baseline = self.peak = rss_reader()
        self.started, self.samples = monotonic(), 0
        self.stopped = Event()
        self.monitor = Thread(target=self._sample, daemon=True)

    def _sample(self):
        while not self.stopped.wait(0.01):
            self.peak = max(self.peak, self.reader())
            self.samples += 1

    def __enter__(self):
        self.check()
        self.monitor.start()
        return self

    def __exit__(self, *args):
        self.stopped.set()
        self.monitor.join()
        self.peak = max(self.peak, self.reader())

    def check(self, allocation=0):
        self.peak = max(self.peak, self.reader())
        self.samples += 1
        require(self.peak-self.baseline <= self.limit and
                self.reader()-self.baseline+allocation <= self.limit,
                'EXPORT_FAILED', 'P5 incremental RSS budget exceeded')

    def summary(self):
        return dict(baseline_rss=self.baseline, peak_rss=self.peak,
                    incremental_peak_rss=self.peak-self.baseline,
                    rss_limit=self.limit, rss_samples=self.samples,
                    sampling_interval_seconds=0.01,
                    elapsed_seconds=monotonic()-self.started)
