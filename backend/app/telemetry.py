"""Minimal Prometheus-style telemetry for evolutionary hardening."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from threading import Lock


def _bucket_name(value_ms: float) -> str:
    if value_ms <= 50:
        return "le_50ms"
    if value_ms <= 150:
        return "le_150ms"
    if value_ms <= 300:
        return "le_300ms"
    if value_ms <= 1000:
        return "le_1000ms"
    return "gt_1000ms"


@dataclass(slots=True)
class LatencySummary:
    count: int = 0
    total_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0


class TelemetryRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._latency_buckets: dict[str, Counter[str]] = defaultdict(Counter)

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def observe_latency(self, name: str, value_ms: float) -> None:
        with self._lock:
            self._latencies[name].append(value_ms)
            self._latency_buckets[name][_bucket_name(value_ms)] += 1

    def counter_value(self, name: str) -> int:
        with self._lock:
            return self._counters[name]

    def latency_summary(self, name: str) -> LatencySummary:
        with self._lock:
            values = sorted(self._latencies.get(name, []))
        if not values:
            return LatencySummary()
        return LatencySummary(
            count=len(values),
            total_ms=round(sum(values), 3),
            p50_ms=_percentile(values, 0.50),
            p95_ms=_percentile(values, 0.95),
            p99_ms=_percentile(values, 0.99),
        )

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            latencies = {key: list(value) for key, value in self._latencies.items()}
            buckets = {key: Counter(value) for key, value in self._latency_buckets.items()}
        for name, value in sorted(counters.items()):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, values in sorted(latencies.items()):
            lines.append(f"# TYPE {name}_ms summary")
            summary = self.latency_summary(name)
            lines.append(f'{name}_ms{{quantile="0.5"}} {summary.p50_ms}')
            lines.append(f'{name}_ms{{quantile="0.95"}} {summary.p95_ms}')
            lines.append(f'{name}_ms{{quantile="0.99"}} {summary.p99_ms}')
            lines.append(f"{name}_ms_sum {summary.total_ms}")
            lines.append(f"{name}_ms_count {summary.count}")
            for bucket_name, bucket_value in sorted(buckets.get(name, Counter()).items()):
                lines.append(f'{name}_bucket{{bucket="{bucket_name}"}} {bucket_value}')
        return "\n".join(lines) + "\n"


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    index = min(max(int(round((len(values) - 1) * ratio)), 0), len(values) - 1)
    return round(values[index], 3)


registry = TelemetryRegistry()
