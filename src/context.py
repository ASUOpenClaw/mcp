"""
Resolve an MCP context token to (workspace_id, user_id).

Two token formats are accepted:

1. Session token (short-lived, minted by Shell proxy):
   - Redis key mcp_ctx:{token} → {"workspace_id": "...", "user_id": "..."}
   - TTL: 300 s, refreshed on every user message.

2. Service token (no Redis entry, for cron jobs and automated agent turns):
   - Format: ws_{workspace_id}_{hmac_sha256_hex}
   - Validated by recomputing HMAC-SHA256(MCP_SERVICE_API_KEY, workspace_id).
   - Never expires; token is deterministic — same workspace_id always yields same token.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass

import redis.asyncio as aioredis
from mcp import McpError
from mcp.types import ErrorData, INVALID_PARAMS

from src.config import settings

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


def _verify_service_token(token: str) -> MCPContext | None:
    """
    Validate a service token (format: ws_{ws_id}_{hmac}).
    Returns MCPContext on success, None if format is wrong or HMAC invalid.
    """
    if not token.startswith("ws_"):
        return None
    # Split on "_" with maxsplit=2: ["ws", ws_id (with hyphens), hmac_hex]
    parts = token.split("_", 2)
    if len(parts) != 3:
        return None
    _, ws_id, provided_sig = parts
    expected_sig = hmac.new(
        settings.service_api_key.encode(),
        ws_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None
    return MCPContext(workspace_id=ws_id, user_id="system")


async def resolve_context(ctx_token: str) -> MCPContext:
    """
    Resolve ctx_token to MCPContext.
    Tries Redis session lookup first; falls back to HMAC service token validation.
    Raises McpError if neither succeeds.
    """
    # 1. Session token — Redis lookup.
    redis = get_redis()
    data = await redis.get(f"mcp_ctx:{ctx_token}")
    if data:
        parsed = json.loads(data)
        return MCPContext(
            workspace_id=parsed["workspace_id"],
            user_id=parsed["user_id"],
        )

    # 2. Service token — HMAC validation, no Redis needed.
    ctx = _verify_service_token(ctx_token)
    if ctx is not None:
        return ctx

    raise McpError(
        ErrorData(
            code=INVALID_PARAMS,
            message="Invalid or expired workspace context. Do not retry with a modified token.",
        )
    )
