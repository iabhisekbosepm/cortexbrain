"""Consolidation Engine — compresses episodic into semantic memory.

Weekly batch job that performs five operations:
1. Promote validated auto-learned knowledge (confidence 0.6 → 0.75)
2. Archive stale low-salience nodes (bottom 10%, 90+ days idle)
3. Merge duplicate/near-duplicate entities
4. Compress long PREVIOUS_VERSION chains
5. Generate consolidation report

All mutations tagged with changed_by='system:consolidation'.
Fully idempotent — safe to re-run.
"""

import difflib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from cortexbrain.config import get_settings
from cortexbrain.memory.meta import MetaMemoryStore
from cortexbrain.memory.semantic import SemanticMemoryStore

logger = logging.getLogger(__name__)

_DEFAULT_ORG = UUID("00000000-0000-0000-0000-000000000000")
_CHANGED_BY = "system:consolidation"


@dataclass
class ConsolidationReport:
    """Report returned after each consolidation run."""

    started_at: str = ""
    completed_at: str = ""
    nodes_promoted: int = 0
    nodes_archived: int = 0
    nodes_merged: int = 0
    merge_nodes_deprecated: int = 0
    version_chains_compressed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "nodes_promoted": self.nodes_promoted,
            "nodes_archived": self.nodes_archived,
            "nodes_merged": self.nodes_merged,
            "merge_nodes_deprecated": self.merge_nodes_deprecated,
            "version_chains_compressed": self.version_chains_compressed,
            "errors": self.errors,
        }


class ConsolidationEngine:
    """Orchestrates the five consolidation operations."""

    def __init__(
        self,
        semantic_memory: SemanticMemoryStore,
        meta_memory: MetaMemoryStore,
    ):
        self.semantic = semantic_memory
        self.meta = meta_memory
        self.settings = get_settings()

    async def run_full_consolidation(self) -> ConsolidationReport:
        """Run all five consolidation operations in sequence. Idempotent."""
        report = ConsolidationReport(
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            await self.promote_validated_knowledge(report)
        except Exception as e:
            logger.error("Promote operation failed: %s", e)
            report.errors.append(f"promote: {e}")

        try:
            await self.archive_stale_nodes(report)
        except Exception as e:
            logger.error("Archive operation failed: %s", e)
            report.errors.append(f"archive: {e}")

        try:
            await self.merge_duplicate_entities(report)
        except Exception as e:
            logger.error("Merge operation failed: %s", e)
            report.errors.append(f"merge: {e}")

        try:
            await self.compress_version_chains(report)
        except Exception as e:
            logger.error("Compress operation failed: %s", e)
            report.errors.append(f"compress: {e}")

        report.completed_at = datetime.now(timezone.utc).isoformat()

        # Record summary in audit log
        await self.meta.record_mutation(
            org_id=_DEFAULT_ORG,
            node_id=_DEFAULT_ORG,
            action="consolidation:summary",
            changed_by=_CHANGED_BY,
            new_value=json.dumps(report.to_dict()),
            reason="Consolidation cycle completed",
        )

        logger.info(
            "Consolidation complete: promoted=%d, archived=%d, merged=%d, compressed=%d, errors=%d",
            report.nodes_promoted,
            report.nodes_archived,
            report.nodes_merged,
            report.version_chains_compressed,
            len(report.errors),
        )

        return report

    # ─── Operation 1: Promote validated auto-learned knowledge ──────────

    async def promote_validated_knowledge(self, report: ConsolidationReport) -> None:
        """Promote auto-learned nodes (confidence ~0.6) that have sufficient evidence.

        Criteria (either):
        - access_count >= consolidation_promotion_min_access (default: 3)
        - 2+ edges to document-sourced nodes (confidence >= 0.7)
        """
        target_conf = self.settings.consolidation_promotion_target_confidence
        min_access = self.settings.consolidation_promotion_min_access

        # Find auto-learned nodes (confidence in 0.55-0.65 range)
        candidates = await self.meta.get_nodes_by_confidence_range(0.55, 0.65)

        for meta in candidates:
            try:
                should_promote = False
                reason = ""

                # Check 1: Sufficient access count
                if meta.access_count >= min_access:
                    should_promote = True
                    reason = f"access_count={meta.access_count} >= {min_access}"
                else:
                    # Check 2: Corroboration by document-sourced neighbors
                    neighbors = await self.semantic.get_neighbors(meta.node_id)
                    high_conf_neighbors = 0
                    for n in neighbors:
                        n_conf = n.get("confidence", 0)
                        if isinstance(n_conf, (int, float)) and n_conf >= 0.7:
                            high_conf_neighbors += 1
                    if high_conf_neighbors >= 2:
                        should_promote = True
                        reason = f"corroborated by {high_conf_neighbors} document-sourced neighbors"

                if should_promote:
                    old_conf = meta.confidence

                    # Update Neo4j
                    await self.semantic.update_node_properties(
                        meta.node_id, {"confidence": target_conf}
                    )

                    # Update M_meta
                    await self.meta.update_metadata(
                        meta.node_id, confidence=target_conf
                    )

                    # Audit log
                    await self.meta.record_mutation(
                        org_id=_DEFAULT_ORG,
                        node_id=meta.node_id,
                        action="consolidation:promote",
                        changed_by=_CHANGED_BY,
                        previous_value=f"confidence={old_conf}",
                        new_value=f"confidence={target_conf}",
                        reason=f"Auto-learned knowledge promoted: {reason}",
                    )

                    report.nodes_promoted += 1

            except Exception as e:
                logger.debug("Promote skipped for %s: %s", meta.node_id, e)

    # ─── Operation 2: Archive stale low-salience nodes ──────────────────

    async def archive_stale_nodes(self, report: ConsolidationReport) -> None:
        """Archive nodes in bottom 10% salience not accessed in 90+ days.

        Archived nodes get status='archived' in Neo4j and are skipped
        by the activation engine. No data is deleted.
        """
        stale_days = self.settings.consolidation_archive_stale_days
        percentile = self.settings.consolidation_archive_salience_percentile

        # Compute salience threshold at the configured percentile
        salience_threshold = await self.meta.compute_salience_percentile(percentile)
        if salience_threshold <= 0:
            return  # No nodes or all zero salience — skip

        # Find stale low-salience nodes
        candidates = await self.meta.get_stale_low_salience_nodes(
            salience_threshold, stale_days
        )

        for meta in candidates:
            try:
                # Check not already archived in Neo4j
                node = await self.semantic.get_node(meta.node_id)
                if node is None:
                    continue
                if str(node.get("status", "")) in ("archived", "merged"):
                    continue

                # Skip recently corrected nodes (user cares about them)
                if meta.correction_count > 0:
                    last_correction_logs = await self.meta.get_node_history(meta.node_id)
                    if last_correction_logs:
                        latest = last_correction_logs[0]
                        if (
                            latest.action == "correction"
                            and latest.timestamp
                            and (datetime.now(timezone.utc) - latest.timestamp).days < 30
                        ):
                            continue

                # Archive the node
                await self.semantic.update_node_properties(
                    meta.node_id, {"status": "archived"}
                )

                days_idle = (
                    datetime.now(timezone.utc) - meta.last_accessed
                ).days if meta.last_accessed else stale_days

                await self.meta.record_mutation(
                    org_id=_DEFAULT_ORG,
                    node_id=meta.node_id,
                    action="consolidation:archive",
                    changed_by=_CHANGED_BY,
                    previous_value=f"status=active, salience={meta.salience:.4f}",
                    new_value="status=archived",
                    reason=f"Low salience ({meta.salience:.4f}) and not accessed in {days_idle} days",
                )

                report.nodes_archived += 1

            except Exception as e:
                logger.debug("Archive skipped for %s: %s", meta.node_id, e)

    # ─── Operation 3: Merge duplicate entities ──────────────────────────

    async def merge_duplicate_entities(self, report: ConsolidationReport) -> None:
        """Merge near-duplicate entities into one authoritative node.

        Uses normalized name matching + difflib similarity scoring.
        Creates MERGED_INTO edges from deprecated to surviving nodes.
        """
        threshold = self.settings.consolidation_merge_name_similarity

        # Fetch all active entities
        entities = await self.semantic.get_all_entities_with_properties()
        if not entities:
            return

        # Normalize names and group
        def _normalize(name: str) -> str:
            n = name.lower().strip()
            # Remove trailing 's' for basic plural handling
            if n.endswith("s") and len(n) > 3:
                n = n[:-1]
            return n

        # Group by normalized name (exact match after normalization)
        name_groups: dict[str, list[dict]] = defaultdict(list)
        for entity in entities:
            name = entity.get("name", "")
            if not name:
                continue
            key = _normalize(name)
            name_groups[key].append(entity)

        # Process groups with 2+ members (exact-match duplicates)
        for norm_name, group in name_groups.items():
            if len(group) < 2:
                continue
            await self._merge_group(group, report)

        # For remaining singletons, find fuzzy matches
        singletons = [
            g[0] for g in name_groups.values() if len(g) == 1
        ]
        if len(singletons) < 2:
            return

        # Pairwise fuzzy matching (capped at 5000 entities for performance)
        if len(singletons) > 5000:
            logger.warning(
                "Consolidation: %d singletons exceeds fuzzy match limit (5000), skipping fuzzy",
                len(singletons),
            )
            return

        matched: set[str] = set()
        for i, a in enumerate(singletons):
            a_id = a.get("id", "")
            if a_id in matched:
                continue
            a_name = a.get("name", "")
            fuzzy_group = [a]

            for b in singletons[i + 1 :]:
                b_id = b.get("id", "")
                if b_id in matched:
                    continue
                b_name = b.get("name", "")
                ratio = difflib.SequenceMatcher(
                    None, a_name.lower(), b_name.lower()
                ).ratio()
                if ratio >= threshold:
                    fuzzy_group.append(b)
                    matched.add(b_id)

            if len(fuzzy_group) >= 2:
                matched.add(a_id)
                await self._merge_group(fuzzy_group, report)

    async def _merge_group(
        self, group: list[dict[str, Any]], report: ConsolidationReport
    ) -> None:
        """Merge a group of duplicate entities into one surviving node."""
        # Pick surviving node: highest confidence → highest access → first by ID
        async def _sort_key(entity: dict) -> tuple:
            node_id = entity.get("id", "")
            conf = float(entity.get("confidence", 0) or 0)
            try:
                meta = await self.meta.get_or_create_metadata(
                    UUID(node_id), _DEFAULT_ORG
                )
                return (-conf, -meta.access_count, node_id)
            except Exception:
                return (-conf, 0, node_id)

        # Sort: best candidate first
        scored = []
        for entity in group:
            key = await _sort_key(entity)
            scored.append((key, entity))
        scored.sort(key=lambda x: x[0])

        surviving = scored[0][1]
        deprecated_list = [s[1] for s in scored[1:]]

        surviving_id = surviving.get("id", "")
        if not surviving_id:
            return

        surviving_uuid = UUID(surviving_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        for dep in deprecated_list:
            dep_id = dep.get("id", "")
            if not dep_id:
                continue
            dep_uuid = UUID(dep_id)

            try:
                # Create MERGED_INTO edge
                await self.semantic.create_merged_into_edge(
                    dep_uuid,
                    surviving_uuid,
                    {"merged_at": now_iso, "merged_by": _CHANGED_BY},
                )

                # Mark deprecated node
                await self.semantic.update_node_properties(
                    dep_uuid, {"status": "merged"}
                )

                # Audit log
                await self.meta.record_mutation(
                    org_id=_DEFAULT_ORG,
                    node_id=dep_uuid,
                    action="consolidation:merge",
                    changed_by=_CHANGED_BY,
                    previous_value=f"name={dep.get('name', '')}",
                    new_value=f"merged_into={surviving_id}",
                    reason=f"Duplicate of '{surviving.get('name', '')}' (id={surviving_id})",
                )

                report.merge_nodes_deprecated += 1

            except Exception as e:
                logger.debug("Merge failed for %s: %s", dep_id, e)

        # Boost surviving node confidence by 0.05 (capped at 0.95)
        old_conf = float(surviving.get("confidence", 0.7) or 0.7)
        new_conf = min(old_conf + 0.05, 0.95)
        try:
            await self.semantic.update_node_properties(
                surviving_uuid, {"confidence": new_conf}
            )
            await self.meta.update_metadata(surviving_uuid, confidence=new_conf)
        except Exception as e:
            logger.debug("Confidence boost failed for %s: %s", surviving_id, e)

        report.nodes_merged += 1

    # ─── Operation 4: Compress version chains ───────────────────────────

    async def compress_version_chains(self, report: ConsolidationReport) -> None:
        """Compress PREVIOUS_VERSION chains longer than max_versions.

        Keeps first version (original), last version (most recent correction),
        and current node. Marks intermediates as compressed=true.
        """
        max_versions = self.settings.consolidation_compress_max_versions

        # Get all entity IDs and check chain lengths
        entity_ids = await self.semantic.get_all_entity_ids()

        for eid_str in entity_ids:
            try:
                eid = UUID(eid_str)
                chain_len = await self.semantic.get_version_chain_length(eid)

                if chain_len <= max_versions:
                    continue

                # Get full chain (oldest first)
                chain = await self.semantic.get_version_chain_nodes(eid)
                if len(chain) <= max_versions:
                    continue

                # Keep: first (index 0), last (index -1). Compress: everything in between
                to_compress = chain[1:-1]  # intermediates

                compressed_count = 0
                for version_node in to_compress:
                    v_id = version_node.get("id")
                    if not v_id:
                        continue
                    # Skip already compressed
                    if version_node.get("compressed"):
                        continue

                    await self.semantic.update_node_properties(
                        UUID(v_id), {"compressed": True}
                    )

                    await self.meta.record_mutation(
                        org_id=_DEFAULT_ORG,
                        node_id=UUID(v_id),
                        action="consolidation:compress",
                        changed_by=_CHANGED_BY,
                        previous_value=f"version={version_node.get('version', '?')}",
                        new_value="compressed=true",
                        reason=f"Intermediate version in chain of {chain_len} for node {eid_str}",
                    )

                    compressed_count += 1

                if compressed_count > 0:
                    report.version_chains_compressed += 1

            except Exception as e:
                logger.debug("Compress skipped for %s: %s", eid_str, e)
