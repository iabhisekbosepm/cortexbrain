"""POST /api/v1/correct — Submit a correction to the knowledge base."""

import uuid

from fastapi import APIRouter, Depends

from cortexbrain.api.deps import get_mutation_engine
from cortexbrain.auth.middleware import verify_api_key
from cortexbrain.core.mutation import MutationEngine
from cortexbrain.models.schemas import CorrectionRequest, CorrectionResponse

router = APIRouter()


@router.post("/correct", response_model=CorrectionResponse)
async def correct(
    request: CorrectionRequest,
    api_key: str = Depends(verify_api_key),
    mutation: MutationEngine = Depends(get_mutation_engine),
):
    """Apply a user correction through the Mutation Engine.

    Pipeline: Locate → Version → Mutate → Meta-Update.
    """
    # TODO: Resolve org_id from API key
    org_id = uuid.uuid4()

    result = await mutation.apply_correction(
        node_id=request.node_id,
        corrected_value=request.corrected_value,
        user_id=request.user_id,
        org_id=org_id,
        reason=request.reason or "",
    )

    return CorrectionResponse(
        status=result["status"],
        version=result["version"],
        node_id=result["node_id"],
        previous_value=result["previous_value"],
        new_value=result["new_value"],
    )
