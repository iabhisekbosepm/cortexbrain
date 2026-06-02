"""Bearer token authentication for CortexBrain API.

MVP uses API key auth (hashed with bcrypt). JWT and SSO/SAML are Phase 2.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_scheme = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> str:
    """Verify Bearer token and return org_id.

    TODO: Look up hashed key in PostgreSQL api_keys table.
    For now, returns a placeholder — will be wired in T6 implementation.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    # TODO: bcrypt verify against api_keys table
    # org_id = await lookup_api_key(token)
    # For scaffolding, accept any non-empty token
    return token
