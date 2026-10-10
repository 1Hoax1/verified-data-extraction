"""Inclusive operational budgets; sampled RSS is not an OS sandbox."""
from pathlib import Path
from .diagnostics import require

RAW = 100_000_000
ROWS = 100_000
COLS = 200
CHUNK = 1_048_576
RSS = 536_870_912


def current_rss():
    # Linux VmRSS is current resident memory, unlike lifetime ru_maxrss.
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1]) * 1024
    raise RuntimeError('Linux RSS measurement unavailable')


class Budget:
    def __init__(self):
        self.baseline = current_rss()
        self.peak = self.baseline

    def check(self):
        rss = current_rss()
        self.peak = max(self.peak, rss)
        require(rss - self.baseline <= RSS, 'RUNTIME_RSS_LIMIT')


def raw_check(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= RAW, 'RAW_BYTE_LIMIT')


class CheckedBytesIO(__import__('io').BytesIO):
    """CSV decoder's buffered reads also sample RSS per <=1 MiB chunk."""
    def __init__(self, raw, budget):
        super().__init__(raw)
        self.budget = budget

    def read1(self, size=-1):
        result = super().read1(CHUNK if size < 0 else min(CHUNK, size))
        self.budget.check()
        return result
