"""Raw Memory (M_r) — Uses Qdrant for fallback vector retrieval.

When the Activation Engine finds no matching entities in the graph,
it falls back to vector similarity search via Qdrant.
"""

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import models

from cortexbrain.config import get_settings

logger = logging.getLogger(__name__)


class RawMemoryStore:
    """Qdrant vector store for CortexBrain's fallback retrieval."""

    def __init__(self, client: QdrantClient | None = None):
        self._client = client

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            settings = get_settings()
            self._client = QdrantClient(url=settings.qdrant_url, timeout=10)
        return self._client

    async def search(self, query_text: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Vector similarity search — used as fallback when activation finds no match.

        Returns empty list if the collection doesn't exist yet (no data ingested).
        """
        try:
            client = self._get_client()
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if "knowledge_nodes" not in collection_names:
                logger.info("No 'knowledge_nodes' collection yet — returning empty results")
                return []

            # Qdrant requires vector for search; for text search we'd need an embedding model.
            # For now, return empty — full embedding pipeline will be wired with ingestion.
            logger.info("Vector search fallback: collection exists but embedding search not yet wired")
            return []
        except Exception as e:
            logger.warning("Vector search fallback failed: %s", e)
            return []
