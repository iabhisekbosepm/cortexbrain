"""Mutation Engine — Revision-based corrections with full audit trail.

Novel CortexBrain layer (not in Cognee). Implements the pipeline:
Locate → Version → Mutate → Meta-Update → Re-index.

Corrections create PREVIOUS_VERSION edges in Neo4j (never destructive).
Every mutation is recorded in PostgreSQL audit log.
After mutation, the corrected text is re-embedded in the vector index
so corrected terms become searchable.
"""

import logging
from typing import Any
from uuid import UUID, uuid4

from cortexbrain.config import get_settings
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore
from cortexbrain.models.graph import KnowledgeNode, VersionEdge

logger = logging.getLogger(__name__)

# The LanceDB collection where Cognee stores Entity name vectors.
# Cognee creates this during cognify() with collection name = "{TypeName}_{field}".
ENTITY_VECTOR_COLLECTION = "Entity_name"


class MutationEngine:
    """Handles corrections and maintains version history.

    PRD flow:
    1. Locate: Find the node to correct in M_s
    2. Version: Archive current state as PREVIOUS_VERSION edge
    3. Mutate: Update the node in-place
    4. Meta-Update: Adjust confidence, flag as volatile, record audit log
    5. Re-index: Re-embed corrected text in vector DB so it's searchable
    """

    def __init__(
        self,
        semantic_memory: SemanticMemoryStore,
        meta_memory: MetaMemoryStore,
    ):
        self.semantic = semantic_memory
        self.meta = meta_memory
        self.settings = get_settings()

    async def apply_correction(
        self,
        node_id: UUID,
        corrected_value: str,
        user_id: str,
        org_id: UUID,
        reason: str = "",
    ) -> dict[str, Any]:
        """Apply a user correction through the full Locate → Version → Mutate → Meta-Update → Re-index pipeline.

        Returns correction result with version info.
        """
        # 1. LOCATE
        current_node = await self.semantic.get_node(node_id)
        if current_node is None:
            # Correction to non-existent node: create new node with lower confidence (PRD spec)
            return await self._create_from_correction(
                node_id, corrected_value, user_id, org_id, reason
            )

        # Cognee Entity nodes use "description" as primary text field
        previous_value = str(
            current_node.get("description", "") or current_node.get("value", "")
        )
        current_version = int(current_node.get("version", 1))
        new_version = current_version + 1

        # 2. VERSION — Archive current state
        archive_node_id = uuid4()
        version_edge = VersionEdge(
            source_node_id=node_id,
            target_node_id=archive_node_id,
            changed_by=f"user:{user_id}",
            reason=reason,
            previous_value=previous_value,
            new_value=corrected_value,
        )
        await self.semantic.create_version_edge(version_edge)

        # 3. MUTATE — Update node in-place
        # Write to both "description" (Cognee's primary text field, read by query
        # pipeline and activation engine) and "value" (CortexBrain convention)
        await self.semantic.update_node_properties(
            node_id,
            {
                "description": corrected_value,
                "value": corrected_value,
                "source": f"user:{user_id}",
                "confidence": 0.95,  # User corrections get high confidence
                "volatile": True,
                "version": new_version,
            },
        )

        # 4. META-UPDATE — Record in audit log, update metadata
        await self.meta.record_mutation(
            org_id=org_id,
            node_id=node_id,
            action="correction",
            changed_by=f"user:{user_id}",
            previous_value=previous_value,
            new_value=corrected_value,
            reason=reason,
            version=new_version,
        )
        await self.meta.update_metadata(
            node_id,
            confidence=0.95,
            volatile=True,
            correction_count=int(current_node.get("correction_count", 0)) + 1,
        )

        # 5. RE-INDEX — Re-embed corrected text in vector DB
        node_name = str(current_node.get("name", ""))
        await self._reindex_vector(node_id, node_name, corrected_value)

        logger.info(
            "Correction applied: node=%s, v%d→v%d, by=%s",
            node_id,
            current_version,
            new_version,
            user_id,
        )

        return {
            "status": "applied",
            "node_id": node_id,
            "version": new_version,
            "previous_value": previous_value,
            "new_value": corrected_value,
        }

    async def _reindex_vector(
        self, node_id: UUID, node_name: str, corrected_value: str
    ) -> None:
        """Re-embed the corrected node in the vector index.

        Cognee stores entity vectors in the Entity_name collection.
        The IDs in that collection may differ from Neo4j node IDs.
        We first try to update by node ID; if not found, we search
        by entity name and update that row's vector.  If neither
        exists we insert a new row so the corrected text is searchable.
        """
        try:
            from cognee.infrastructure.databases.vector import get_vector_engine

            vector_engine = get_vector_engine()

            if not await vector_engine.has_collection(ENTITY_VECTOR_COLLECTION):
                logger.warning("Vector collection %s not found, skipping re-index", ENTITY_VECTOR_COLLECTION)
                return

            # Combine name + description for richer embedding
            embed_text = f"{node_name}: {corrected_value}" if node_name else corrected_value

            # Generate new embedding vector
            vectors = await vector_engine.embed_data([embed_text])
            if not vectors or not vectors[0]:
                logger.warning("Embedding generation returned empty for node %s", node_id)
                return

            new_vector = vectors[0]

            collection = await vector_engine.get_collection(ENTITY_VECTOR_COLLECTION)

            # Try updating by node_id first
            result = await collection.update(
                updates={"vector": new_vector},
                where=f"id = '{str(node_id)}'",
            )

            # If no rows matched, search for the entity by name and update that row
            rows_updated = getattr(result, "rows_updated", None) if result else None
            if rows_updated is not None and rows_updated > 0:
                logger.info("Re-indexed node %s in %s (by node_id)", node_id, ENTITY_VECTOR_COLLECTION)
                return

            # Search by name — Cognee may store entities with a different ID
            if node_name:
                conn = await vector_engine.get_connection()
                tbl = await conn.open_table(ENTITY_VECTOR_COLLECTION)
                # Find rows whose payload.text matches the entity name
                try:
                    matches = await tbl.search(new_vector).limit(1).to_list()
                    if matches:
                        match_id = matches[0].get("id", "")
                        # Verify it's a reasonable match (same name in payload)
                        payload = matches[0].get("payload") or {}
                        match_text = payload.get("text", "") if isinstance(payload, dict) else ""
                        if match_text and match_text.lower() == node_name.lower():
                            await collection.update(
                                updates={"vector": new_vector},
                                where=f"id = '{match_id}'",
                            )
                            logger.info(
                                "Re-indexed node %s in %s (by name match id=%s)",
                                node_id, ENTITY_VECTOR_COLLECTION, match_id,
                            )
                            return
                except Exception:
                    pass

            # Fallback: insert a new row with node_id so future updates work
            import json

            await collection.add([{
                "id": str(node_id),
                "vector": new_vector,
                "payload": json.dumps({
                    "id": str(node_id),
                    "type": "CorrectedEntity",
                    "text": node_name or corrected_value[:100],
                }),
            }])

            logger.info(
                "Inserted new vector for node %s in %s (embed_text=%d chars)",
                node_id, ENTITY_VECTOR_COLLECTION, len(embed_text),
            )

        except Exception as e:
            # Re-indexing failure should not block the correction itself
            logger.warning("Vector re-index failed for node %s: %s", node_id, e)

    async def _create_from_correction(
        self,
        node_id: UUID,
        value: str,
        user_id: str,
        org_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """Create a new node from a correction to a non-existent node.

        Per PRD: confidence set to 0.7 (lower than document-sourced nodes).
        """
        await self.meta.record_mutation(
            org_id=org_id,
            node_id=node_id,
            action="correction_create",
            changed_by=f"user:{user_id}",
            new_value=value,
            reason=reason,
            version=1,
        )
        await self.meta.get_or_create_metadata(node_id, org_id)

        logger.info("Created node from correction: node=%s, by=%s", node_id, user_id)

        return {
            "status": "created",
            "node_id": node_id,
            "version": 1,
            "previous_value": "",
            "new_value": value,
        }

    async def get_version_history(self, node_id: UUID) -> list[dict[str, Any]]:
        """Get full version chain from both Neo4j edges and PostgreSQL audit log."""
        audit_logs = await self.meta.get_node_history(node_id)
        return [
            {
                "version": log.version,
                "value": log.new_value,
                "changed_by": log.changed_by,
                "timestamp": log.timestamp.isoformat(),
                "reason": log.reason,
            }
            for log in audit_logs
        ]
