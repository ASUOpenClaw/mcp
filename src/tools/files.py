from __future__ import annotations

import mimetypes
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..context import resolve_context
from .. import rest_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_files(
        ctx_token: str,
        folder_id: str | None = None,
        search: str | None = None,
        mime_type: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List files in the workspace or a specific folder.

        Args:
            ctx_token: Workspace context token from the system prompt.
            folder_id: Filter to a specific folder UUID (optional).
            search: Search by file name (optional).
            mime_type: Filter by MIME type (optional).
            page: Page number (default 1).
            per_page: Results per page (default 20, max 100).
        """
        ctx = await resolve_context(ctx_token)
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if folder_id:
            params["folder_id"] = folder_id
        if search:
            params["search"] = search
        if mime_type:
            params["mime_type"] = mime_type
        return await rest_client.get(ctx, f"/workspaces/{ctx.workspace_id}/files", params=params)

    @mcp.tool()
    async def get_file(
        ctx_token: str,
        file_id: str,
    ) -> dict[str, Any]:
        """Get metadata for a specific file.

        Args:
            ctx_token: Workspace context token from the system prompt.
            file_id: UUID of the file to retrieve.
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.get(ctx, f"/workspaces/{ctx.workspace_id}/files/{file_id}")

    @mcp.tool()
    async def get_download_url(
        ctx_token: str,
        file_id: str,
    ) -> dict[str, Any]:
        """Get a presigned S3 download URL for a file (valid 1 hour).

        Args:
            ctx_token: Workspace context token from the system prompt.
            file_id: UUID of the file to download.
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.get(ctx, f"/workspaces/{ctx.workspace_id}/files/{file_id}/download")

    @mcp.tool()
    async def get_file_status(
        ctx_token: str,
        file_id: str,
    ) -> dict[str, Any]:
        """Check the indexing status of a file after upload.
        Poll this after create_file until indexing_status is 'completed' or 'failed'
        before using rag_search to query its contents.

        Args:
            ctx_token: Workspace context token from the system prompt.
            file_id: UUID of the file to check.
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.get(ctx, f"/workspaces/{ctx.workspace_id}/files/{file_id}")

    @mcp.tool()
    async def create_file(
        ctx_token: str,
        filename: str,
        content: str,
        folder_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new text file in the workspace with the given content.
        The file is automatically indexed for RAG search after upload.

        Args:
            ctx_token: Workspace context token from the system prompt.
            filename: File name including extension (e.g. "report.md", "notes.txt").
            content: Full text content to write into the file.
            folder_id: UUID of the folder to place the file in (optional).
            description: Short description of the file (optional).
        """
        MAX_BYTES = 5 * 1024 * 1024  # 5 MB
        ctx = await resolve_context(ctx_token)
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise ValueError(
                f"content too large: {len(encoded):,} bytes (max {MAX_BYTES:,})"
            )
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = "text/plain"
        form: dict[str, str] = {"auto_index": "true"}
        if folder_id:
            form["folder_id"] = folder_id
        if description:
            form["description"] = description
        return await rest_client.post_multipart(
            ctx,
            f"/workspaces/{ctx.workspace_id}/files",
            filename=filename,
            content=encoded,
            mime_type=mime_type,
            form_fields=form,
        )
