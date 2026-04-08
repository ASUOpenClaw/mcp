"""
MCP server entry point.
Registers all tools and starts the FastMCP server.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .config import settings
from .context import init_redis
from . import rest_client
from .tools import rag, files, folders, conversations, transcriptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="openclaw-workspace",
    instructions=(
        "Tools for searching the workspace knowledge base, listing files, folders, "
        "and conversations. Every tool requires ctx_token — pass the token from the "
        "[WORKSPACE_CTX: mcp_ctx=...] system prompt unchanged."
    ),
)

# Register all tool groups
rag.register(mcp)
files.register(mcp)
folders.register(mcp)
conversations.register(mcp)
transcriptions.register(mcp)


def main() -> None:
    logger.info("Initialising Redis: %s", settings.redis_url)
    init_redis(settings.redis_url)
    logger.info("Initialising REST client: %s", settings.rest_url)
    rest_client.init(pool_size=settings.http_pool_size)
    logger.info("Starting MCP server on %s:%d", settings.host, settings.port)
    try:
        mcp.run(transport="streamable-http", host=settings.host, port=settings.port)
    finally:
        import asyncio
        asyncio.run(rest_client.close())


if __name__ == "__main__":
    main()
