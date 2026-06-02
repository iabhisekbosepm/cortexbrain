"""Celery tasks for CortexBrain background processing.

- decay_cycle_task: Runs every 30s, decrements activation scores
- batch_ingestion_task: Processes large document batches asynchronously
- salience_recompute_task: Hourly recompute of salience scores
- consolidation_task: Weekly episodic-to-semantic memory compression
- text_ingestion_task: Async text ingestion for hooks

All tasks emit pipeline stage events via PipelineEventEmitter for
real-time monitoring on the /pipeline frontend page.
"""

import asyncio
import logging

from cortexbrain.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code from sync Celery tasks.

    Uses asyncio.run() which properly sets the event loop as current
    for the thread, avoiding 'Future attached to a different loop' errors
    from Cognee/SQLAlchemy internals.
    """
    return asyncio.run(coro)


def _get_emitter(pipeline: str, total_stages: int, task=None):
    """Create a PipelineEventEmitter, returning None if import fails."""
    try:
        from cortexbrain.workers.pipeline_events import PipelineEventEmitter
        task_id = task.request.id if task else None
        return PipelineEventEmitter(pipeline, total_stages, task_id=task_id)
    except Exception:
        return None


class _NoopEmitter:
    """Fallback emitter that does nothing — used when Redis is unavailable."""
    def pipeline_started(self): pass
    def pipeline_completed(self, metrics=None): pass
    def stage_started(self, idx, name): pass
    def stage_completed(self, idx, name, metrics=None): pass
    def stage_failed(self, idx, name, error=""): pass


@celery_app.task(name="cortexbrain.workers.tasks.decay_cycle_task")
def decay_cycle_task():
    """Periodic task: decay activation scores across all sessions.

    Per PRD: runs every 30s, decrements by DECAY_RATE, evicts nodes at 0.
    Nodes evicted from Redis remain in Neo4j — no data is lost.

    Stages: scan_sessions → decrement_scores → evict_expired
    """
    from cortexbrain.core.activation.decay import DecayCycle
    from cortexbrain.memory.active import ActiveMemoryStore

    emitter = _get_emitter("decay", 3, decay_cycle_task) or _NoopEmitter()
    emitter.pipeline_started()

    try:
        # Stage 0: Scan sessions
        emitter.stage_started(0, "scan_sessions")
        active = ActiveMemoryStore()
        cycle = DecayCycle(active_memory=active)
        emitter.stage_completed(0, "scan_sessions")

        # Stage 1: Decrement scores
        emitter.stage_started(1, "decrement_scores")
        report = _run_async(cycle.run_cycle())
        emitter.stage_completed(1, "decrement_scores", {
            "sessions_processed": len(report),
        })

        # Stage 2: Evict expired
        emitter.stage_started(2, "evict_expired")
        total_evicted = sum(len(v) for v in report.values())
        emitter.stage_completed(2, "evict_expired", {
            "nodes_evicted": total_evicted,
        })

        result = {"sessions_processed": len(report), "total_evicted": total_evicted}
        emitter.pipeline_completed(result)

        if total_evicted > 0:
            logger.info("Decay cycle complete: %d nodes evicted across %d sessions",
                         total_evicted, len(report))
        return result

    except Exception as e:
        emitter.stage_failed(0, "decay", str(e))
        raise


@celery_app.task(name="cortexbrain.workers.tasks.batch_ingestion_task")
def batch_ingestion_task(data_path: str, dataset_name: str = "default"):
    """Async batch ingestion for large document sets.

    Wraps Cognee's add() + cognify() for background execution.

    Stages: cognee_add → cognee_cognify → meta_init
    """
    from cortexbrain.ingestion.documents import ingest_documents

    emitter = _get_emitter("ingestion", 3, batch_ingestion_task) or _NoopEmitter()
    emitter.pipeline_started()

    try:
        emitter.stage_started(0, "cognee_add")
        # ingest_documents handles all 3 stages internally
        # We emit stage events around the full call since the function is atomic
        result = _run_async(ingest_documents(data=data_path, dataset_name=dataset_name))
        emitter.stage_completed(0, "cognee_add")

        emitter.stage_started(1, "cognee_cognify")
        emitter.stage_completed(1, "cognee_cognify")

        emitter.stage_started(2, "meta_init")
        nodes_init = result.get("nodes_initialized", 0)
        emitter.stage_completed(2, "meta_init", {"nodes_initialized": nodes_init})

        emitter.pipeline_completed(result)
        logger.info("Batch ingestion complete: %s", result)
        return result

    except Exception as e:
        emitter.stage_failed(0, "cognee_add", str(e))
        emitter.pipeline_completed({"error": str(e)})
        raise


@celery_app.task(name="cortexbrain.workers.tasks.text_ingestion_task")
def text_ingestion_task(text: str, dataset_name: str = "default"):
    """Async text ingestion — queued via Celery for non-blocking callers.

    Same as synchronous /ingest/text but runs in a worker process.
    Used by Claude Code hooks that need fire-and-forget semantics.

    Stages: cognee_add → cognee_cognify → meta_init
    """
    from cortexbrain.ingestion.documents import ingest_documents

    emitter = _get_emitter("ingestion", 3, text_ingestion_task) or _NoopEmitter()
    emitter.pipeline_started()

    try:
        emitter.stage_started(0, "cognee_add")
        result = _run_async(ingest_documents(data=text, dataset_name=dataset_name))
        emitter.stage_completed(0, "cognee_add")

        emitter.stage_started(1, "cognee_cognify")
        emitter.stage_completed(1, "cognee_cognify")

        emitter.stage_started(2, "meta_init")
        nodes_init = result.get("nodes_initialized", 0)
        emitter.stage_completed(2, "meta_init", {"nodes_initialized": nodes_init})

        emitter.pipeline_completed(result)
        logger.info("Text ingestion complete (dataset=%s): %s", dataset_name, result)
        return result

    except Exception as e:
        emitter.stage_failed(0, "cognee_add", str(e))
        emitter.pipeline_completed({"error": str(e)})
        raise


@celery_app.task(name="cortexbrain.workers.tasks.consolidation_task")
def consolidation_task():
    """Weekly consolidation: promote, archive, merge, compress, report.

    Compresses episodic memory into semantic memory. All changes
    tagged with changed_by='system:consolidation'.

    Stages: promote_validated → archive_stale → merge_duplicates →
            compress_versions → generate_report
    """
    from cortexbrain.core.consolidation import ConsolidationEngine
    from cortexbrain.memory.meta import MetaMemoryStore
    from cortexbrain.memory.semantic import SemanticMemoryStore

    emitter = _get_emitter("consolidation", 5, consolidation_task) or _NoopEmitter()
    emitter.pipeline_started()

    async def _consolidate():
        engine = ConsolidationEngine(
            semantic_memory=SemanticMemoryStore(),
            meta_memory=MetaMemoryStore(),
        )

        from cortexbrain.core.consolidation.engine import ConsolidationReport
        from datetime import datetime, timezone
        report = ConsolidationReport(started_at=datetime.now(timezone.utc).isoformat())

        # Stage 0: Promote validated knowledge
        emitter.stage_started(0, "promote_validated")
        try:
            await engine.promote_validated_knowledge(report)
            emitter.stage_completed(0, "promote_validated", {
                "nodes_promoted": report.nodes_promoted,
            })
        except Exception as e:
            emitter.stage_failed(0, "promote_validated", str(e))
            report.errors.append(f"promote: {e}")

        # Stage 1: Archive stale nodes
        emitter.stage_started(1, "archive_stale")
        try:
            await engine.archive_stale_nodes(report)
            emitter.stage_completed(1, "archive_stale", {
                "nodes_archived": report.nodes_archived,
            })
        except Exception as e:
            emitter.stage_failed(1, "archive_stale", str(e))
            report.errors.append(f"archive: {e}")

        # Stage 2: Merge duplicates
        emitter.stage_started(2, "merge_duplicates")
        try:
            await engine.merge_duplicate_entities(report)
            emitter.stage_completed(2, "merge_duplicates", {
                "nodes_merged": report.nodes_merged,
                "nodes_deprecated": report.merge_nodes_deprecated,
            })
        except Exception as e:
            emitter.stage_failed(2, "merge_duplicates", str(e))
            report.errors.append(f"merge: {e}")

        # Stage 3: Compress version chains
        emitter.stage_started(3, "compress_versions")
        try:
            await engine.compress_version_chains(report)
            emitter.stage_completed(3, "compress_versions", {
                "chains_compressed": report.version_chains_compressed,
            })
        except Exception as e:
            emitter.stage_failed(3, "compress_versions", str(e))
            report.errors.append(f"compress: {e}")

        # Stage 4: Generate report
        emitter.stage_started(4, "generate_report")
        report.completed_at = datetime.now(timezone.utc).isoformat()
        import json
        await engine.meta.record_mutation(
            org_id=engine.meta._default_org if hasattr(engine.meta, '_default_org') else __import__('uuid').UUID("00000000-0000-0000-0000-000000000000"),
            node_id=__import__('uuid').UUID("00000000-0000-0000-0000-000000000000"),
            action="consolidation:summary",
            changed_by="system:consolidation",
            new_value=json.dumps(report.to_dict()),
            reason="Consolidation cycle completed",
        )
        emitter.stage_completed(4, "generate_report", {
            "errors": len(report.errors),
        })

        return report

    try:
        report = _run_async(_consolidate())
        report_dict = report.to_dict()
        emitter.pipeline_completed(report_dict)
        logger.info("Consolidation complete: %s", report_dict)
        return report_dict
    except Exception as e:
        emitter.stage_failed(0, "consolidation", str(e))
        raise


@celery_app.task(name="cortexbrain.workers.tasks.salience_recompute_task")
def salience_recompute_task():
    """Periodic task: recompute salience scores for all Entity nodes.

    Iterates all Entity nodes in Neo4j, fetches access_count/recency/corrections
    from PostgreSQL NodeMetadata, counts edges in Neo4j, and updates salience.

    Stages: fetch_entities → fetch_metadata → compute_scores → update_scores
    """
    from uuid import UUID

    from cortexbrain.core.metacognition import SalienceScorer
    from cortexbrain.memory.meta import MetaMemoryStore
    from cortexbrain.memory.semantic import SemanticMemoryStore

    emitter = _get_emitter("salience", 4, salience_recompute_task) or _NoopEmitter()
    emitter.pipeline_started()

    async def _recompute():
        semantic = SemanticMemoryStore()
        meta = MetaMemoryStore()
        scorer = SalienceScorer()

        # Stage 0: Fetch entities
        emitter.stage_started(0, "fetch_entities")
        entity_ids = await semantic.get_all_entity_ids()
        emitter.stage_completed(0, "fetch_entities", {
            "entity_count": len(entity_ids),
        })

        # Stage 1: Fetch metadata
        emitter.stage_started(1, "fetch_metadata")
        emitter.stage_completed(1, "fetch_metadata", {
            "entities_to_process": len(entity_ids),
        })

        # Stage 2: Compute scores
        emitter.stage_started(2, "compute_scores")
        updated = 0
        for eid_str in entity_ids:
            try:
                node_id = UUID(eid_str)
                metadata = await meta.get_or_create_metadata(
                    node_id=node_id,
                    org_id=UUID("00000000-0000-0000-0000-000000000000"),
                )
                edge_count = await semantic.get_edge_count(node_id)
                salience = scorer.compute(
                    access_count=metadata.access_count,
                    last_accessed_ts=metadata.last_accessed.timestamp(),
                    correction_count=metadata.correction_count,
                    edge_count=edge_count,
                )
                await meta.update_metadata(node_id, salience=salience)
                updated += 1
            except Exception as e:
                logger.debug("Salience recompute skipped for %s: %s", eid_str, e)
        emitter.stage_completed(2, "compute_scores", {
            "nodes_computed": updated,
        })

        # Stage 3: Update scores (already done inline, just mark complete)
        emitter.stage_started(3, "update_scores")
        emitter.stage_completed(3, "update_scores", {
            "nodes_updated": updated,
        })

        return updated

    try:
        updated = _run_async(_recompute())
        emitter.pipeline_completed({"nodes_updated": updated})
        logger.info("Salience recompute complete: %d nodes updated", updated)
        return {"nodes_updated": updated}
    except Exception as e:
        emitter.stage_failed(0, "fetch_entities", str(e))
        raise
