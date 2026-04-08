"""
Resolve an MCP context token to (workspace_id, user_id) via Redis lookup.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import redis.asyncio as aioredis
from mcp.server.fastmcp import FastMCP
from mcp import McpError
from mcp.types import ErrorData, INVALID_PARAMS

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
    """Look up ctx_token in Redis. Raises McpError if missing or expired."""
    redis = get_redis()
    key = f"mcp_ctx:{ctx_token}"
    data = await redis.get(key)
    if not data:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message="Invalid or expired workspace context. Do not retry with a modified token.",
            )
        )
    parsed = json.loads(data)
    return MCPContext(
        workspace_id=parsed["workspace_id"],
        user_id=parsed["user_id"],
    )
