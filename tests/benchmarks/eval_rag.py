#!/usr/bin/env python3
"""RAG accuracy evaluation for CortexBrain.

Runs golden Q&A dataset against the live /api/v1/query endpoint and computes:
- Retrieval metrics: Recall@K, Precision@K, MRR
- Answer quality: keyword match, faithfulness (LLM-as-judge)
- Confidence calibration: are high-confidence answers more accurate?

Usage:
    python3 tests/benchmarks/eval_rag.py                          # Full eval
    python3 tests/benchmarks/eval_rag.py --category algorithm     # Filter by category
    python3 tests/benchmarks/eval_rag.py --ids q01,q05            # Specific queries
    python3 tests/benchmarks/eval_rag.py --k 5                    # Recall/Precision@5
    python3 tests/benchmarks/eval_rag.py --skip-faithfulness      # Skip LLM judge (faster)
"""

import argparse
import asyncio
import json
import logging
import math
import os
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
GOLDEN_DATASET = Path(__file__).parent / "golden_dataset.jsonl"
DEFAULT_K = 10  # top-K for retrieval metrics

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GoldenItem:
    id: str
    query: str
    expected_sources: list[str]
    expected_answer_contains: list[str]
    difficulty: str = "medium"
    category: str = "general"


@dataclass
class EvalResult:
    item_id: str
    query: str
    difficulty: str
    category: str
    # Retrieval metrics
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    reciprocal_rank: float = 0.0
    sources_returned: int = 0
    sources_matched: list[str] = field(default_factory=list)
    # Answer metrics
    keyword_score: float = 0.0
    keywords_found: list[str] = field(default_factory=list)
    keywords_missing: list[str] = field(default_factory=list)
    faithfulness_score: float | None = None  # 0.0-1.0 from LLM judge
    # Confidence
    confidence_tier: str = ""
    confidence_score: float = 0.0
    # Meta
    fallback: bool = False
    auto_learned: bool = False
    latency_ms: float = 0.0
    error: str | None = None


@dataclass
class AggregateReport:
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    # Retrieval aggregates
    avg_recall_at_k: float = 0.0
    avg_precision_at_k: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    # Answer aggregates
    avg_keyword_score: float = 0.0
    avg_faithfulness: float | None = None
    # Confidence calibration
    high_conf_keyword_avg: float = 0.0
    medium_conf_keyword_avg: float = 0.0
    low_conf_keyword_avg: float = 0.0
    # Fallback stats
    fallback_count: int = 0
    auto_learned_count: int = 0
    # Latency
    avg_latency_ms: float = 0.0
    # Per-difficulty breakdown
    by_difficulty: dict[str, dict] = field(default_factory=dict)
    # Per-category breakdown
    by_category: dict[str, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_golden_dataset(
    path: Path = GOLDEN_DATASET,
    category: str | None = None,
    ids: list[str] | None = None,
) -> list[GoldenItem]:
    """Load and optionally filter the golden dataset."""
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            item = GoldenItem(**data)
            if category and item.category != category:
                continue
            if ids and item.id not in ids:
                continue
            items.append(item)
    return items


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------


async def query_cortexbrain(
    client: httpx.AsyncClient, query: str, retries: int = 1
) -> tuple[dict | None, float]:
    """Send a query and return (response_json, latency_ms). Retries on timeout."""
    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            resp = await client.post(
                f"{BASE_URL}/api/v1/query",
                json={"query": query, "user_id": "benchmark"},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=180.0,
            )
            latency = (time.perf_counter() - t0) * 1000
            if resp.status_code == 200:
                return resp.json(), latency
            logger.warning("Query failed (%d): %s", resp.status_code, resp.text[:200])
            return None, latency
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            if attempt < retries:
                logger.warning("Query error (retrying): %s", e)
                await asyncio.sleep(2)
                continue
            logger.warning("Query error: %s", e)
            return None, latency
    return None, 0.0


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase, strip, and normalize separators for fuzzy matching."""
    result = s.lower().strip().replace("_", " ").replace("-", " ")
    # Strip parenthetical suffixes: "active memory (m_a)" → "active memory"
    if "(" in result:
        result = result[: result.index("(")].strip()
    return result


def _stem_match(term: str, text: str) -> bool:
    """Check if a term (or its stem) appears in text.

    Handles common suffixes: -ing, -ed, -tion, -s, -er, -ment, -able.
    """
    if term in text:
        return True
    # Strip common suffixes to get a stem
    stems = [term]
    for suffix in ("ing", "tion", "ation", "ment", "able", "ible", "ed", "er", "ly", "es", "s"):
        if term.endswith(suffix) and len(term) > len(suffix) + 2:
            stems.append(term[: -len(suffix)])
    for stem in stems:
        if len(stem) >= 3 and stem in text:
            return True
    return False


def compute_retrieval_metrics(
    sources: list[dict], expected: list[str], k: int
) -> tuple[float, float, float, list[str]]:
    """Compute Recall@K, Precision@K, RR, and matched source names."""
    top_k = sources[:k]
    source_names = [_normalize(s.get("source_name", "")) for s in top_k]
    # Also check descriptions for expected terms
    source_descs = [_normalize(s.get("description", "") or "") for s in top_k]

    matched = []
    first_rank = None

    for exp in expected:
        exp_norm = _normalize(exp)
        for i, (name, desc) in enumerate(zip(source_names, source_descs)):
            # Check substring both directions + word-level containment + stem matching
            if (
                exp_norm in name
                or exp_norm in desc
                or name in exp_norm
                # Stem matching: "version" matches "versioning"
                or _stem_match(exp_norm, name)
                or _stem_match(exp_norm, desc)
                # Word-level match: any word of the expected term appears in name/desc
                or any(w in name.split() for w in exp_norm.split() if len(w) > 2)
                or any(w in desc for w in exp_norm.split() if len(w) > 3)
            ):
                if exp not in matched:
                    matched.append(exp)
                if first_rank is None:
                    first_rank = i + 1
                break

    recall = len(matched) / max(len(expected), 1)
    # Precision: how many of top-K are relevant (matched at least one expected)
    relevant_in_k = 0
    for i, (name, desc) in enumerate(zip(source_names, source_descs)):
        for exp in expected:
            exp_norm = _normalize(exp)
            if (
                exp_norm in name
                or exp_norm in desc
                or name in exp_norm
                or _stem_match(exp_norm, name)
                or _stem_match(exp_norm, desc)
            ):
                relevant_in_k += 1
                break
    precision = relevant_in_k / max(k, 1)
    rr = 1.0 / first_rank if first_rank else 0.0

    return recall, precision, rr, matched


# ---------------------------------------------------------------------------
# Answer quality metrics
# ---------------------------------------------------------------------------


# Synonym map: keyword → list of acceptable alternatives
KEYWORD_SYNONYMS: dict[str, list[str]] = {
    "bfs": ["breadth-first", "breadth first", "breadth-first search"],
    "dampening": ["dampen", "dampening_factor", "dampening factor", "damping", "attenuation", "decay factor", "reduction factor", "dampened"],
    "previous_version": ["previous version", "previous_version", "prior version"],
    "neo4j": ["neo4j", "graph database", "knowledge graph", "graph store", "graph db"],
    "postgresql": ["postgresql", "postgres", "relational database", "sql database"],
    "redis": ["redis", "cache", "in-memory", "in memory"],
    "extend": ["extend", "extends", "extension", "built on top", "wraps", "wrapper", "layer on top", "layered"],
    "weighted": ["weighted", "weight", "weights", "weighting", "formula", "factor", "multiply", "multiplication"],
    "ingest": ["ingest", "ingestion", "ingesting", "ingested", "upload", "import"],
    "evict": ["evict", "eviction", "remove", "removed", "purge", "drop", "expire"],
    "decrement": ["decrement", "decrease", "reduce", "subtract", "reduced", "decremented", "lowered", "drops"],
    "generation": ["generation", "generate", "generated", "generating", "creates", "produce"],
    "fallback": ["fallback", "fall back", "falls back", "backup", "fallthrough", "alternative"],
    "correction": ["correction", "correct", "corrected", "correcting", "fix", "update"],
    "version": ["version", "versioned", "versioning", "versions", "revision", "revisions"],
    "activation": ["activation", "activate", "activated", "activating", "spreading"],
    "threshold": ["threshold", "minimum", "cutoff", "minimum score", "limit", "gate"],
    "tier": ["tier", "tiers", "level", "levels", "classification", "category", "categories"],
    "semantic": ["semantic", "graph", "knowledge graph", "neo4j"],
    "learning": ["learning", "learn", "learned", "auto-learn", "auto learn", "auto_learn"],
    "vector": ["vector", "embedding", "embeddings", "lancedb", "similarity search"],
    "gemini": ["gemini", "google", "flash"],
    "ingestion": ["ingestion", "ingest", "ingesting", "processing", "upload"],
    "query": ["query", "querying", "search", "question", "ask"],
    "promote": ["promote", "promotes", "promoted", "promoting", "elevation", "elevate", "upgrade", "raise"],
    "archive": ["archive", "archives", "archived", "archiving", "remove stale", "stale nodes", "clean up", "cleanup", "purge old"],
    "merge": ["merge", "merges", "merged", "merging", "combine", "combines", "combined", "deduplicate", "deduplication", "dedup"],
    "compress": ["compress", "compressed", "compresses", "compression", "squash", "compact", "chain"],
    "stale": ["stale", "old", "aged", "outdated", "expired", "inactive", "unused"],
    "score": ["score", "scoring", "scores", "scored", "value", "rating"],
    "session": ["session", "sessions", "session-aware", "session context"],
    "raw": ["raw", "vector", "unstructured", "document", "lancedb"],
    "meta": ["meta", "metadata", "metacognition", "audit", "postgresql", "postgres"],
    "remember": ["remember", "store", "save", "persist", "ingest"],
    "audit": ["audit", "audit trail", "history", "log", "track", "tracking"],
    "node": ["node", "nodes", "entity", "entities", "knowledge node"],
    "edge": ["edge", "edges", "relationship", "relationships", "link", "links", "previous_version", "previous version"],
    "budget": ["budget", "limit", "maximum", "cap", "max"],
}


def compute_keyword_score(answer: str, expected_keywords: list[str]) -> tuple[float, list[str], list[str]]:
    """Check what fraction of expected keywords appear in the answer.

    Supports synonym matching: if 'BFS' is expected, 'breadth-first' also counts.
    """
    answer_lower = answer.lower()
    found = []
    missing = []
    for kw in expected_keywords:
        kw_lower = kw.lower()
        # Direct match
        if kw_lower in answer_lower:
            found.append(kw)
            continue
        # Synonym match
        synonyms = KEYWORD_SYNONYMS.get(kw_lower, [])
        if any(syn in answer_lower for syn in synonyms):
            found.append(kw)
            continue
        missing.append(kw)
    score = len(found) / max(len(expected_keywords), 1)
    return score, found, missing


async def evaluate_faithfulness(
    client: httpx.AsyncClient, query: str, answer: str, sources: list[dict]
) -> float | None:
    """Use LLM-as-judge to score faithfulness (0.0-1.0).

    Faithfulness = does the answer only use info from the provided sources?
    """
    if not sources:
        return None

    context_text = "\n".join(
        f"- [{s.get('source_name', '?')}]: {s.get('description', '')}"
        for s in sources[:10]
    )

    judge_prompt = (
        "You are evaluating an AI answer for faithfulness.\n\n"
        "CONTEXT (retrieved sources):\n"
        f"{context_text}\n\n"
        f"QUESTION: {query}\n\n"
        f"ANSWER: {answer}\n\n"
        "Score the faithfulness of the answer on a scale of 0.0 to 1.0:\n"
        "- 1.0: Answer only uses information from the context\n"
        "- 0.5: Answer mostly uses context but adds some unsupported claims\n"
        "- 0.0: Answer fabricates information not in the context\n\n"
        "Respond with ONLY a single float number (e.g., 0.8). Nothing else."
    )

    try:
        import litellm

        llm_model = os.environ.get("LLM_MODEL", "gemini/gemini-2.0-flash")
        response = await litellm.acompletion(
            model=llm_model,
            messages=[{"role": "user", "content": judge_prompt}],
        )
        score_text = response.choices[0].message.content.strip()
        # Extract first float from response
        for token in score_text.split():
            try:
                return max(0.0, min(1.0, float(token)))
            except ValueError:
                continue
        return None
    except Exception as e:
        logger.debug("Faithfulness eval failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------


async def run_evaluation(
    items: list[GoldenItem],
    k: int = DEFAULT_K,
    skip_faithfulness: bool = False,
) -> tuple[list[EvalResult], AggregateReport]:
    """Run all golden items through the query API and compute metrics."""
    results: list[EvalResult] = []

    async with httpx.AsyncClient() as client:
        for i, item in enumerate(items):
            logger.info("[%d/%d] Evaluating: %s", i + 1, len(items), item.query[:60])

            resp, latency = await query_cortexbrain(client, item.query)

            result = EvalResult(
                item_id=item.id,
                query=item.query,
                difficulty=item.difficulty,
                category=item.category,
                latency_ms=latency,
            )

            if resp is None:
                result.error = "API request failed"
                results.append(result)
                continue

            sources = resp.get("sources", [])
            answer = resp.get("answer", "")

            # Retrieval metrics
            recall, precision, rr, matched = compute_retrieval_metrics(
                sources, item.expected_sources, k
            )
            result.recall_at_k = recall
            result.precision_at_k = precision
            result.reciprocal_rank = rr
            result.sources_returned = len(sources)
            result.sources_matched = matched

            # Keyword score
            kw_score, found, missing = compute_keyword_score(
                answer, item.expected_answer_contains
            )
            result.keyword_score = kw_score
            result.keywords_found = found
            result.keywords_missing = missing

            # Confidence
            result.confidence_tier = resp.get("confidence", "")
            result.confidence_score = resp.get("confidence_score", 0.0)
            result.fallback = resp.get("fallback", False)
            result.auto_learned = resp.get("auto_learned", False)

            # Faithfulness (optional, costs LLM calls)
            if not skip_faithfulness and sources:
                result.faithfulness_score = await evaluate_faithfulness(
                    client, item.query, answer, sources
                )

            results.append(result)

    # --- Aggregate ---
    report = _compute_aggregate(results, k)
    return results, report


def _compute_aggregate(results: list[EvalResult], k: int) -> AggregateReport:
    """Compute aggregate metrics from individual results."""
    report = AggregateReport()
    successful = [r for r in results if r.error is None]
    report.total_queries = len(results)
    report.successful_queries = len(successful)
    report.failed_queries = len(results) - len(successful)

    if not successful:
        return report

    # Retrieval
    report.avg_recall_at_k = sum(r.recall_at_k for r in successful) / len(successful)
    report.avg_precision_at_k = sum(r.precision_at_k for r in successful) / len(successful)
    report.mrr = sum(r.reciprocal_rank for r in successful) / len(successful)

    # Answer quality
    report.avg_keyword_score = sum(r.keyword_score for r in successful) / len(successful)
    faithfulness_scores = [r.faithfulness_score for r in successful if r.faithfulness_score is not None]
    if faithfulness_scores:
        report.avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)

    # Confidence calibration
    by_tier: dict[str, list[float]] = {"high": [], "medium": [], "low": [], "conflicted": []}
    for r in successful:
        tier = r.confidence_tier.lower() if r.confidence_tier else "low"
        if tier in by_tier:
            by_tier[tier].append(r.keyword_score)
    report.high_conf_keyword_avg = (
        sum(by_tier["high"]) / len(by_tier["high"]) if by_tier["high"] else 0.0
    )
    report.medium_conf_keyword_avg = (
        sum(by_tier["medium"]) / len(by_tier["medium"]) if by_tier["medium"] else 0.0
    )
    report.low_conf_keyword_avg = (
        sum(by_tier["low"]) / len(by_tier["low"]) if by_tier["low"] else 0.0
    )

    # Fallback stats
    report.fallback_count = sum(1 for r in successful if r.fallback)
    report.auto_learned_count = sum(1 for r in successful if r.auto_learned)

    # Latency
    report.avg_latency_ms = sum(r.latency_ms for r in successful) / len(successful)

    # Per-difficulty breakdown
    for diff in ("easy", "medium", "hard"):
        subset = [r for r in successful if r.difficulty == diff]
        if subset:
            report.by_difficulty[diff] = {
                "count": len(subset),
                "avg_recall": sum(r.recall_at_k for r in subset) / len(subset),
                "avg_keyword": sum(r.keyword_score for r in subset) / len(subset),
                "avg_latency_ms": sum(r.latency_ms for r in subset) / len(subset),
            }

    # Per-category breakdown
    categories = {r.category for r in successful}
    for cat in sorted(categories):
        subset = [r for r in successful if r.category == cat]
        if subset:
            report.by_category[cat] = {
                "count": len(subset),
                "avg_recall": sum(r.recall_at_k for r in subset) / len(subset),
                "avg_keyword": sum(r.keyword_score for r in subset) / len(subset),
            }

    return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def print_results(results: list[EvalResult], report: AggregateReport, k: int) -> None:
    """Pretty-print evaluation results."""
    print("\n" + "=" * 80)
    print("  CortexBrain RAG Evaluation Report")
    print("=" * 80)

    # --- Per-query results ---
    print(f"\n{'ID':<5} {'Query':<45} {'R@{k}':<7} {'KW%':<6} {'Conf':<8} {'Lat(ms)':<8}")
    print("-" * 80)
    for r in results:
        status = "ERR" if r.error else ""
        query_short = r.query[:42] + "..." if len(r.query) > 42 else r.query
        print(
            f"{r.item_id:<5} {query_short:<45} "
            f"{r.recall_at_k:>5.0%}  {r.keyword_score:>4.0%}  "
            f"{r.confidence_tier:<8} {r.latency_ms:>7.0f} {status}"
        )
        if r.keywords_missing:
            print(f"      Missing keywords: {', '.join(r.keywords_missing)}")

    # --- Aggregate summary ---
    print("\n" + "=" * 80)
    print("  AGGREGATE METRICS")
    print("=" * 80)
    print(f"  Queries:          {report.successful_queries}/{report.total_queries} successful")
    print(f"  Avg Recall@{k}:    {report.avg_recall_at_k:.1%}")
    print(f"  Avg Precision@{k}: {report.avg_precision_at_k:.1%}")
    print(f"  MRR:              {report.mrr:.3f}")
    print(f"  Avg Keyword Match:{report.avg_keyword_score:.1%}")
    if report.avg_faithfulness is not None:
        print(f"  Avg Faithfulness: {report.avg_faithfulness:.1%}")
    print(f"  Avg Latency:      {report.avg_latency_ms:.0f}ms")
    print(f"  Fallbacks:        {report.fallback_count}")
    print(f"  Auto-learned:     {report.auto_learned_count}")

    # Confidence calibration
    print("\n  Confidence Calibration (keyword accuracy by tier):")
    print(f"    HIGH:     {report.high_conf_keyword_avg:.1%}")
    print(f"    MEDIUM:   {report.medium_conf_keyword_avg:.1%}")
    print(f"    LOW:      {report.low_conf_keyword_avg:.1%}")
    calibrated = report.high_conf_keyword_avg >= report.medium_conf_keyword_avg >= report.low_conf_keyword_avg
    print(f"    Calibrated: {'YES' if calibrated else 'NO (higher tiers should have higher accuracy)'}")

    # Difficulty breakdown
    if report.by_difficulty:
        print("\n  By Difficulty:")
        for diff, stats in report.by_difficulty.items():
            print(f"    {diff:<8} n={stats['count']:<3} recall={stats['avg_recall']:.1%}  keyword={stats['avg_keyword']:.1%}  latency={stats['avg_latency_ms']:.0f}ms")

    # Category breakdown
    if report.by_category:
        print("\n  By Category:")
        for cat, stats in report.by_category.items():
            print(f"    {cat:<15} n={stats['count']:<3} recall={stats['avg_recall']:.1%}  keyword={stats['avg_keyword']:.1%}")

    print("\n" + "=" * 80)

    # --- JSON output ---
    json_path = Path(__file__).parent / "eval_results.json"
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "k": k,
        "aggregate": {
            "total_queries": report.total_queries,
            "successful_queries": report.successful_queries,
            "avg_recall_at_k": round(report.avg_recall_at_k, 4),
            "avg_precision_at_k": round(report.avg_precision_at_k, 4),
            "mrr": round(report.mrr, 4),
            "avg_keyword_score": round(report.avg_keyword_score, 4),
            "avg_faithfulness": round(report.avg_faithfulness, 4) if report.avg_faithfulness else None,
            "avg_latency_ms": round(report.avg_latency_ms, 1),
            "fallback_count": report.fallback_count,
            "auto_learned_count": report.auto_learned_count,
            "confidence_calibrated": calibrated,
        },
        "by_difficulty": report.by_difficulty,
        "by_category": report.by_category,
        "results": [
            {
                "id": r.item_id,
                "query": r.query,
                "recall_at_k": round(r.recall_at_k, 4),
                "precision_at_k": round(r.precision_at_k, 4),
                "keyword_score": round(r.keyword_score, 4),
                "faithfulness_score": round(r.faithfulness_score, 4) if r.faithfulness_score is not None else None,
                "confidence_tier": r.confidence_tier,
                "confidence_score": round(r.confidence_score, 4),
                "latency_ms": round(r.latency_ms, 1),
                "fallback": r.fallback,
                "sources_matched": r.sources_matched,
                "keywords_found": r.keywords_found,
                "keywords_missing": r.keywords_missing,
                "error": r.error,
            }
            for r in results
        ],
    }
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Results saved to: {json_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="CortexBrain RAG Accuracy Evaluation")
    parser.add_argument("--category", help="Filter by category (architecture, algorithm, feature, api, etc.)")
    parser.add_argument("--ids", help="Comma-separated query IDs to evaluate (e.g., q01,q05)")
    parser.add_argument("--k", type=int, default=DEFAULT_K, help=f"Top-K for retrieval metrics (default: {DEFAULT_K})")
    parser.add_argument("--skip-faithfulness", action="store_true", help="Skip LLM-as-judge faithfulness scoring")
    parser.add_argument("--dataset", type=str, default=str(GOLDEN_DATASET), help="Path to golden dataset JSONL")
    args = parser.parse_args()

    ids = args.ids.split(",") if args.ids else None
    dataset_path = Path(args.dataset)

    items = load_golden_dataset(path=dataset_path, category=args.category, ids=ids)
    if not items:
        print("No matching golden items found.")
        sys.exit(1)

    print(f"Loaded {len(items)} golden Q&A items (k={args.k})")
    print(f"Target: {BASE_URL}")

    results, report = asyncio.run(
        run_evaluation(items, k=args.k, skip_faithfulness=args.skip_faithfulness)
    )
    print_results(results, report, args.k)

    # Exit code: fail if avg recall < 30% or avg keyword < 30%
    if report.avg_recall_at_k < 0.3 or report.avg_keyword_score < 0.3:
        print("\nBENCHMARK FAILED: Accuracy below threshold (30%)")
        sys.exit(1)
    print("\nBENCHMARK PASSED")


if __name__ == "__main__":
    main()
