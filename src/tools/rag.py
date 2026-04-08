from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..context import resolve_context
from .. import rest_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def rag_search(
        ctx_token: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.4,
        folder_id: str | None = None,
        mime_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search the workspace knowledge base for relevant document chunks.

        Args:
            ctx_token: Workspace context token from the system prompt.
            query: Natural language search query.
            top_k: Maximum number of results to return (default 5).
            min_score: Minimum relevance score threshold (default 0.4).
            folder_id: Restrict search to a specific folder UUID.
            mime_types: Restrict search to specific MIME types (e.g. ["application/pdf"]).
        """
        ctx = await resolve_context(ctx_token)
        body = {
            "query": query,
            "top_k": top_k,
            "min_score": min_score,
            "filters": {
                "folder_id": folder_id,
                "mime_types": mime_types,
            },
        }
        return await rest_client.post(ctx, f"/workspaces/{ctx.workspace_id}/rag/search", body)
