from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import rest_client
from ..context import resolve_context


def register(mcp: FastMCP) -> None:

    @mcp.tool(structured_output=False)
    async def list_folders(
        ctx_token: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """List folders in the workspace.

        Args:
            ctx_token: Workspace context token from the system prompt [WORKSPACE_CTX].
            parent_id: List children of this folder UUID. Omit to list root folders.
        """
        ctx = await resolve_context(ctx_token)
        params: dict[str, Any] = {}
        if parent_id:
            params["parent_id"] = parent_id
        return await rest_client.get(
            ctx, f"/workspaces/{ctx.workspace_id}/folders", params=params
        )
