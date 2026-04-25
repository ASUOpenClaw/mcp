"""
Resolve a ctx_token to MCPContext (workspace_id + owner_user_id).

Authentication: ctx_token is an HMAC-SHA256 service token derived from the workspace_id.
Format: ws_{workspace_id}_{hmac_sha256_hex}
Shared secret: settings.service_api_key (MCP_SERVICE_API_KEY env var).

The shell proxy injects this token into the agent's system prompt so the model
passes it as ctx_token to every ws__ tool call. MCP verifies the HMAC locally
without Redis round-trip, then looks up owner_user_id from ws_creds.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import logging
from dataclasses import dataclass

import redis.asyncio as aioredis

from mcp import McpError
from mcp.types import INVALID_PARAMS, ErrorData

from .config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


def init_redis(url: str) -> None:
    global _redis
    _redis = aioredis.from_url(url, decode_responses=True)


def get_redis() -> aioredis.Redis:
    assert _redis is not None, "Redis not initialised"
    return _redis


@dataclass
class MCPContext:
    workspace_id: str
    user_id: str


async def resolve_context(ctx_token: str) -> MCPContext:
    """
    Validate an HMAC service token and resolve to MCPContext.

    Token format: ws_{workspace_id}_{sha256_hex}
    Verifies HMAC before any Redis lookup — tampered tokens are rejected immediately.
    Raises McpError(INVALID_PARAMS) for bad tokens or unknown workspaces.
    """
    try:
        parts = ctx_token.split("_", 2)
        if len(parts) != 3 or parts[0] != "ws":
            raise ValueError("wrong prefix or part count")
        _, workspace_id, sig = parts
    except ValueError:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message="Invalid ctx_token format. Expected ws_{workspace_id}_{hmac_sha256}.",
            )
        )

    expected = _hmac.new(
        settings.service_api_key.encode(),
        workspace_id.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not _hmac.compare_digest(expected, sig):
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message="Invalid ctx_token signature.",
            )
        )

    redis = get_redis()
    creds_raw = await redis.get(f"ws_creds:{workspace_id}")
    if not creds_raw:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=f"Unknown workspace '{workspace_id}'. Ensure the workspace is provisioned and ws_creds are set.",
            )
        )
    try:
        creds = json.loads(creds_raw)
        owner_user_id = creds.get("owner_user_id")
        if not owner_user_id:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message=f"Workspace '{workspace_id}' is missing owner_user_id in ws_creds. Re-provision the workspace.",
                )
            )
    except (json.JSONDecodeError, KeyError) as exc:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=f"Invalid ws_creds for workspace '{workspace_id}': {exc}",
            )
        )
    return MCPContext(workspace_id=workspace_id, user_id=owner_user_id)
