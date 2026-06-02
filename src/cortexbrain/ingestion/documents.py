"""Document ingestion — Uses Cognee's add() and cognify() pipeline.

CortexBrain does NOT re-implement ingestion. It wraps Cognee's ECL pipeline
and adds post-processing: conflict detection, M_meta initialization.
"""

import logging
from typing import Any
from uuid import UUID

import cognee
from cognee.modules.users.methods import get_default_user

from cortexbrain.core.metacognition import SalienceScorer
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore

logger = logging.getLogger(__name__)

# Default org for dev mode
_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")


async def _init_metadata_for_new_entities(
    semantic: SemanticMemoryStore,
    meta: MetaMemoryStore,
    org_id: UUID,
) -> int:
    """Create M_meta entries and compute initial salience for all Entity nodes.

    Idempotent: get_or_create_metadata() skips nodes that already have entries.
    Returns count of newly initialized nodes.
    """
    entity_ids = await semantic.get_all_entity_ids()
    scorer = SalienceScorer()
    initialized = 0

    for eid_str in entity_ids:
        try:
            node_id = UUID(eid_str)
            metadata = await meta.get_or_create_metadata(node_id=node_id, org_id=org_id)

            # Compute initial salience
            edge_count = await semantic.get_edge_count(node_id)
            salience = scorer.compute(
                access_count=metadata.access_count,
                last_accessed_ts=metadata.last_accessed.timestamp(),
                correction_count=metadata.correction_count,
                edge_count=edge_count,
            )
            await meta.update_metadata(node_id, salience=salience)
            initialized += 1
        except Exception as e:
            logger.debug("M_meta init skipped for %s: %s", eid_str, e)

    return initialized


async def ingest_documents(
    data: Any,
    dataset_name: str = "default",
    org_id: UUID | None = None,
) -> dict[str, Any]:
    """Ingest documents via Cognee's ECL pipeline, then initialize CortexBrain metadata.

    Steps:
    1. cognee.add() — Ingest into Cognee's data store
    2. cognee.cognify() — Extract entities, build knowledge graph
    3. Initialize M_meta entries for new nodes (confidence, salience)
    """
    user = await get_default_user()
    effective_org = org_id or _DEFAULT_ORG

    # Step 1: Cognee ingestion
    await cognee.add(data, dataset_name=dataset_name)

    # Step 2: Cognee knowledge graph construction
    await cognee.cognify(datasets=[dataset_name], user=user)

    # Step 3: Initialize M_meta for new Entity nodes
    semantic = SemanticMemoryStore()
    meta = MetaMemoryStore()
    initialized = await _init_metadata_for_new_entities(semantic, meta, effective_org)

    logger.info(
        "Document ingestion complete for dataset=%s, initialized %d node metadata entries",
        dataset_name,
        initialized,
    )

    return {"status": "ingested", "dataset": dataset_name, "nodes_initialized": initialized}


async def ingest_slack_export(
    slack_json_path: str,
    dataset_name: str = "slack_export",
    org_id: UUID | None = None,
) -> dict[str, Any]:
    """Ingest Slack JSON export via Cognee's pipeline.

    Cognee handles the raw text processing. CortexBrain adds:
    - Correction detection in threads ("Actually, the DB is on port 5433 not 5432")
    - Filtering of emoji-only messages (handled pre-ingestion)
    """
    user = await get_default_user()
    await cognee.add(slack_json_path, dataset_name=dataset_name)
    await cognee.cognify(datasets=[dataset_name], user=user)

    return {"status": "ingested", "dataset": dataset_name, "source_type": "slack"}


async def ingest_git_repo(
    repo_url: str,
    dataset_name: str = "git_repo",
    org_id: UUID | None = None,
) -> dict[str, Any]:
    """Ingest a Git repository via Cognee's pipeline.

    Cognee handles code parsing (Tree-sitter for ASTs).
    CortexBrain adds: config file key-value extraction as KnowledgeNodes.
    """
    user = await get_default_user()
    await cognee.add(repo_url, dataset_name=dataset_name)
    await cognee.cognify(datasets=[dataset_name], user=user)

    return {"status": "ingested", "dataset": dataset_name, "source_type": "git"}
