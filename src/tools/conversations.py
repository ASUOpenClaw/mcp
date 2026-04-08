from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..context import resolve_context
from .. import rest_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_conversations(
        ctx_token: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List the user's conversations in this workspace.

        Args:
            ctx_token: Workspace context token from the system prompt.
            page: Page number (default 1).
            per_page: Results per page (default 20).
        """
        ctx = await resolve_context(ctx_token)
        params = {"page": page, "per_page": per_page}
        return await rest_client.get(ctx, f"/workspaces/{ctx.workspace_id}/conversations", params=params)

    @mcp.tool()
    async def get_conversation_messages(
        ctx_token: str,
        conversation_id: str,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Get paginated messages from a conversation.

        Args:
            ctx_token: Workspace context token from the system prompt.
            conversation_id: UUID of the conversation.
            page: Page number (default 1).
            per_page: Messages per page (default 50).
        """
        ctx = await resolve_context(ctx_token)
        params = {"page": page, "per_page": per_page}
        return await rest_client.get(
            ctx,
            f"/workspaces/{ctx.workspace_id}/conversations/{conversation_id}/messages",
            params=params,
        )
