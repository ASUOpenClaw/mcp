from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .. import rest_client
from ..context import resolve_context


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def transcribe_file(
        ctx_token: str,
        file_id: str,
        language: str | None = None,
        include_timestamps: bool = True,
    ) -> dict[str, Any]:
        """Submit an audio or video file for transcription via Whisper.
        Returns immediately with task_id and status='processing'.
        Use get_transcription(task_id) to poll until status is 'completed' or 'failed'.

        Args:
            ctx_token: Workspace context token from the system prompt [WORKSPACE_CTX].
            file_id: UUID of the audio/video file to transcribe.
            language: ISO 639-1 language code (e.g. 'en', 'ru'). Auto-detected if omitted.
            include_timestamps: Whether to include word/segment timestamps in the result.
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.post(
            ctx,
            f"/workspaces/{ctx.workspace_id}/transcribe",
            body={
                "file_id": file_id,
                "language": language,
                "include_timestamps": include_timestamps,
            },
        )

    @mcp.tool()
    async def get_transcription(
        ctx_token: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Get the status and result of a transcription task.
        Poll this after transcribe_file until status is 'completed' or 'failed'.
        When completed, transcription_id is set — use list_transcriptions or
        get_transcription_record to retrieve the full result with both files.

        Args:
            ctx_token: Workspace context token from the system prompt [WORKSPACE_CTX].
            task_id: UUID returned by transcribe_file.
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.get(
            ctx,
            f"/workspaces/{ctx.workspace_id}/transcribe/{task_id}",
        )

    @mcp.tool()
    async def list_transcriptions(
        ctx_token: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List all completed transcriptions in the workspace.
        Each item includes audio_file (original recording) and transcript_file
        (indexed text file, searchable via rag_search).

        Args:
            ctx_token: Workspace context token from the system prompt [WORKSPACE_CTX].
            page: Page number (default 1).
            per_page: Results per page (default 20, max 100).
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.get(
            ctx,
            f"/workspaces/{ctx.workspace_id}/transcriptions",
            params={"page": page, "per_page": per_page},
        )

    @mcp.tool()
    async def get_transcription_record(
        ctx_token: str,
        transcription_id: str,
    ) -> dict[str, Any]:
        """Get a single transcription with full audio and transcript file details.
        Returns audio_file.id and transcript_file.id for use with other file tools.

        Args:
            ctx_token: Workspace context token from the system prompt [WORKSPACE_CTX].
            transcription_id: UUID of the transcription record.
        """
        ctx = await resolve_context(ctx_token)
        return await rest_client.get(
            ctx,
            f"/workspaces/{ctx.workspace_id}/transcriptions/{transcription_id}",
        )
