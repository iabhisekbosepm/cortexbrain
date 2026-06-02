#!/usr/bin/env python3
"""Speed benchmark for CortexBrain RAG pipeline.

Measures latency of the full /api/v1/query endpoint and individual components.
Runs N iterations per query and reports p50, p95, p99 percentiles.

Usage:
    python3 tests/benchmarks/bench_speed.py                    # Default (5 queries x 3 iterations)
    python3 tests/benchmarks/bench_speed.py --iterations 10    # More iterations for stable stats
    python3 tests/benchmarks/bench_speed.py --queries 3        # Fewer queries
    python3 tests/benchmarks/bench_speed.py --threshold 5000   # Fail if p95 > 5000ms
    python3 tests/benchmarks/bench_speed.py --component        # Benchmark individual components
"""

import argparse
import asyncio
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("CORTEXBRAIN_URL", "http://localhost:8000")
API_KEY = os.environ.get("CORTEXBRAIN_API_KEY", "test-key")
DEFAULT_ITERATIONS = 3
DEFAULT_P95_THRESHOLD_MS = 45000  # 45s default (includes LLM generation latency)

# Benchmark queries — varied complexity to stress different pipeline stages
BENCH_QUERIES = [
    {"label": "simple_entity", "query": "What is spreading activation?"},
    {"label": "multi_entity", "query": "How do the four memory substrates work together?"},
    {"label": "specific_detail", "query": "What is the dampening factor for activation?"},
    {"label": "broad_topic", "query": "Explain the full query pipeline from start to finish"},
    {"label": "correction_flow", "query": "How does the correction and versioning system work?"},
    {"label": "out_of_domain", "query": "What is the capital of France?"},
    {"label": "algorithm_detail", "query": "How is salience score computed for a knowledge node?"},
    {"label": "infrastructure", "query": "What Celery tasks run on a schedule?"},
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LatencyStats:
    label: str
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.latencies_ms)

    @property
    def p50(self) -> float:
        return self._percentile(50) if self.latencies_ms else 0.0

    @property
    def p95(self) -> float:
        return self._percentile(95) if self.latencies_ms else 0.0

    @property
    def p99(self) -> float:
        return self._percentile(99) if self.latencies_ms else 0.0

    @property
    def mean(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.latencies_ms) if len(self.latencies_ms) > 1 else 0.0

    @property
    def min_ms(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0.0

    def _percentile(self, pct: int) -> float:
        sorted_data = sorted(self.latencies_ms)
        idx = (pct / 100) * (len(sorted_data) - 1)
        lower = int(idx)
        upper = min(lower + 1, len(sorted_data) - 1)
        frac = idx - lower
        return sorted_data[lower] * (1 - frac) + sorted_data[upper] * frac


@dataclass
class ComponentTiming:
    """Timing breakdown from a single query's response insights."""
    total_ms: float = 0.0
    sources_count: int = 0
    activation_mode: str = ""
    fallback: bool = False
    confidence_tier: str = ""


# ---------------------------------------------------------------------------
# Benchmark runners
# ---------------------------------------------------------------------------


async def bench_e2e_query(
    client: httpx.AsyncClient, query: str
) -> tuple[float, ComponentTiming]:
    """Benchmark a single query E2E. Returns (latency_ms, component_timing)."""
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{BASE_URL}/api/v1/query",
            json={"query": query, "user_id": "benchmark-speed"},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60.0,
        )
        latency = (time.perf_counter() - t0) * 1000

        timing = ComponentTiming(total_ms=latency)
        if resp.status_code == 200:
            data = resp.json()
            timing.sources_count = len(data.get("sources", []))
            insights = data.get("insights", {}) or {}
            timing.activation_mode = insights.get("activation_mode", "unknown")
            timing.fallback = data.get("fallback", False)
            timing.confidence_tier = data.get("confidence", "")
        return latency, timing
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        logger.warning("Query failed: %s", e)
        return latency, ComponentTiming(total_ms=latency)


async def bench_health(client: httpx.AsyncClient) -> float:
    """Benchmark health endpoint (baseline latency)."""
    t0 = time.perf_counter()
    try:
        await client.get(
            f"{BASE_URL}/api/v1/health",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10.0,
        )
    except Exception:
        pass
    return (time.perf_counter() - t0) * 1000


async def bench_component_endpoints(client: httpx.AsyncClient, iterations: int) -> dict[str, LatencyStats]:
    """Benchmark individual endpoints for component-level timing."""
    stats: dict[str, LatencyStats] = {
        "health": LatencyStats(label="Health check (baseline)"),
        "query_simple": LatencyStats(label="Query (simple entity)"),
        "query_complex": LatencyStats(label="Query (multi-entity)"),
        "query_ood": LatencyStats(label="Query (out-of-domain)"),
    }

    for i in range(iterations):
        logger.info("  Component iteration %d/%d", i + 1, iterations)

        # Health (baseline)
        lat = await bench_health(client)
        stats["health"].latencies_ms.append(lat)

        # Simple query
        lat, _ = await bench_e2e_query(client, "What is spreading activation?")
        stats["query_simple"].latencies_ms.append(lat)

        # Complex query
        lat, _ = await bench_e2e_query(client, "Explain how the four memory substrates interact during a query with corrections")
        stats["query_complex"].latencies_ms.append(lat)

        # Out-of-domain (triggers continuous learning)
        lat, _ = await bench_e2e_query(client, "What is quantum computing?")
        stats["query_ood"].latencies_ms.append(lat)

    return stats


async def run_speed_benchmark(
    num_queries: int, iterations: int, component_mode: bool
) -> tuple[dict[str, LatencyStats], list[ComponentTiming]]:
    """Run the full speed benchmark suite."""
    queries = BENCH_QUERIES[:num_queries]
    per_query_stats: dict[str, LatencyStats] = {}
    all_timings: list[ComponentTiming] = []

    async with httpx.AsyncClient() as client:
        # --- Warmup ---
        logger.info("Warming up (1 query)...")
        await bench_e2e_query(client, "warmup query")

        # --- E2E query benchmarks ---
        logger.info("Running E2E benchmarks (%d queries x %d iterations)...", len(queries), iterations)
        for q in queries:
            stats = LatencyStats(label=q["label"])
            for i in range(iterations):
                lat, timing = await bench_e2e_query(client, q["query"])
                stats.latencies_ms.append(lat)
                all_timings.append(timing)
                logger.info("  [%s] iter %d: %.0fms (sources=%d, mode=%s)",
                            q["label"], i + 1, lat, timing.sources_count, timing.activation_mode)
            per_query_stats[q["label"]] = stats

        # --- Component benchmarks (optional) ---
        component_stats: dict[str, LatencyStats] = {}
        if component_mode:
            logger.info("\nRunning component benchmarks (%d iterations)...", iterations)
            component_stats = await bench_component_endpoints(client, iterations)

    # Merge all stats
    all_stats = {**per_query_stats, **component_stats}

    # Add an "overall" aggregate
    all_latencies = []
    for s in per_query_stats.values():
        all_latencies.extend(s.latencies_ms)
    if all_latencies:
        overall = LatencyStats(label="OVERALL (all queries)")
        overall.latencies_ms = all_latencies
        all_stats["__overall__"] = overall

    return all_stats, all_timings


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_speed_report(
    stats: dict[str, LatencyStats],
    timings: list[ComponentTiming],
    threshold_ms: float,
) -> bool:
    """Pretty-print speed benchmark results. Returns True if passed."""
    print("\n" + "=" * 90)
    print("  CortexBrain Speed Benchmark Report")
    print("=" * 90)

    print(f"\n{'Label':<35} {'N':>4} {'p50':>8} {'p95':>8} {'p99':>8} {'mean':>8} {'stdev':>8}")
    print("-" * 90)

    overall_p95 = 0.0
    for key, s in stats.items():
        if key == "__overall__":
            overall_p95 = s.p95
            print("-" * 90)
        print(f"{s.label:<35} {s.count:>4} {s.p50:>7.0f}ms {s.p95:>7.0f}ms {s.p99:>7.0f}ms {s.mean:>7.0f}ms {s.stdev:>7.0f}ms")

    # --- Activation mode distribution ---
    modes: dict[str, int] = {}
    for t in timings:
        mode = t.activation_mode or "unknown"
        modes[mode] = modes.get(mode, 0) + 1
    if modes:
        print("\n  Activation Mode Distribution:")
        for mode, count in sorted(modes.items(), key=lambda x: -x[1]):
            print(f"    {mode:<25} {count:>3} ({count / len(timings):.0%})")

    # --- Fallback stats ---
    fallback_count = sum(1 for t in timings if t.fallback)
    if timings:
        print(f"\n  Fallback Rate: {fallback_count}/{len(timings)} ({fallback_count / len(timings):.0%})")

    # --- Pass/fail ---
    passed = overall_p95 <= threshold_ms
    print(f"\n  p95 Threshold: {threshold_ms:.0f}ms")
    print(f"  Actual p95:    {overall_p95:.0f}ms")
    print(f"  Status:        {'PASSED' if passed else 'FAILED'}")

    # --- JSON output ---
    json_path = Path(__file__).parent / "speed_results.json"
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "threshold_ms": threshold_ms,
        "passed": passed,
        "overall_p95_ms": round(overall_p95, 1),
        "queries": {
            key: {
                "label": s.label,
                "count": s.count,
                "p50_ms": round(s.p50, 1),
                "p95_ms": round(s.p95, 1),
                "p99_ms": round(s.p99, 1),
                "mean_ms": round(s.mean, 1),
                "stdev_ms": round(s.stdev, 1),
                "min_ms": round(s.min_ms, 1),
                "max_ms": round(s.max_ms, 1),
            }
            for key, s in stats.items()
        },
        "activation_modes": modes,
        "fallback_rate": fallback_count / max(len(timings), 1),
    }
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {json_path}")
    print("=" * 90)

    return passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="CortexBrain Speed Benchmark")
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Iterations per query (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--queries", "-q", type=int, default=len(BENCH_QUERIES),
                        help=f"Number of benchmark queries (default: {len(BENCH_QUERIES)})")
    parser.add_argument("--threshold", "-t", type=float, default=DEFAULT_P95_THRESHOLD_MS,
                        help=f"p95 threshold in ms (default: {DEFAULT_P95_THRESHOLD_MS})")
    parser.add_argument("--component", "-c", action="store_true",
                        help="Also run component-level benchmarks")
    args = parser.parse_args()

    print(f"Speed benchmark: {min(args.queries, len(BENCH_QUERIES))} queries x {args.iterations} iterations")
    print(f"Target: {BASE_URL}")
    print(f"p95 threshold: {args.threshold}ms")

    stats, timings = asyncio.run(
        run_speed_benchmark(args.queries, args.iterations, args.component)
    )
    passed = print_speed_report(stats, timings, args.threshold)

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
