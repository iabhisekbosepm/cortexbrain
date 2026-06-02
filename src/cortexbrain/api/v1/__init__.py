from fastapi import APIRouter

from . import agent_query, consolidation, correct, dashboard, datasets, debug, graph, health, ingest, nodes, pipeline, query, review, timeline, workers

router = APIRouter(prefix="/api/v1")
router.include_router(query.router, tags=["Query"])
router.include_router(correct.router, tags=["Corrections"])
router.include_router(nodes.router, tags=["Nodes"])
router.include_router(health.router, tags=["Health"])
router.include_router(ingest.router, tags=["Ingestion"])
router.include_router(datasets.router, tags=["Datasets"])
router.include_router(consolidation.router, tags=["Consolidation"])
router.include_router(debug.router, tags=["Debug"])
router.include_router(workers.router, tags=["Workers"])
router.include_router(timeline.router, tags=["Timeline"])
router.include_router(agent_query.router, tags=["Agent Query"])
router.include_router(graph.router, tags=["Graph"])
router.include_router(dashboard.router, tags=["Dashboard"])
router.include_router(review.router, tags=["Review"])
router.include_router(pipeline.router, tags=["Pipeline"])
