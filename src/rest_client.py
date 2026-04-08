"""
HTTP client pool for the REST API.

Maintains a pool of httpx.AsyncClient instances to multiply available
connections. A single client caps at max_connections (httpx default: 100);
under burst load all slots fill and requests queue or fail. Pool of N clients
gives N * max_connections headroom.

Call init() at startup, close() at shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx

from .config import settings
from .context import MCPContext

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
UPLOAD_TIMEOUT = 30.0

_pool: asyncio.Queue[httpx.AsyncClient] | None = None


def init(pool_size: int = 20) -> None:
    global _pool
    _pool = asyncio.Queue(maxsize=pool_size)
    for _ in range(pool_size):
        _pool.put_nowait(httpx.AsyncClient(timeout=DEFAULT_TIMEOUT))
    logger.info("REST client pool initialised (%d clients)", pool_size)


async def close() -> None:
    global _pool
    if _pool is not None:
        while not _pool.empty():
            client = _pool.get_nowait()
            await client.aclose()
        _pool = None
        logger.info("REST client pool closed")


@asynccontextmanager
async def _acquire() -> AsyncGenerator[httpx.AsyncClient, None]:
    if _pool is None:
        raise RuntimeError("rest_client not initialised — call rest_client.init() at startup")
    client = await _pool.get()
    try:
        yield client
    finally:
        await _pool.put(client)


def _service_headers(ctx: MCPContext) -> dict[str, str]:
    return {
        "X-Service-Key": settings.service_api_key,
        "X-On-Behalf-Of-User": ctx.user_id,
        # workspace_id comes from URL path, not header — no X-On-Behalf-Of-Workspace needed
    }


async def get(ctx: MCPContext, path: str, params: dict | None = None) -> Any:
    url = f"{settings.rest_url}{path}"
    async with _acquire() as client:
        resp = await client.get(url, headers=_service_headers(ctx), params=params)
        resp.raise_for_status()
        return resp.json()


async def post(ctx: MCPContext, path: str, body: dict) -> Any:
    url = f"{settings.rest_url}{path}"
    async with _acquire() as client:
        resp = await client.post(url, headers=_service_headers(ctx), json=body)
        resp.raise_for_status()
        return resp.json()


async def post_multipart(
    ctx: MCPContext,
    path: str,
    filename: str,
    content: bytes,
    mime_type: str,
    form_fields: dict[str, str] | None = None,
) -> Any:
    url = f"{settings.rest_url}{path}"
    files = {"file": (filename, content, mime_type)}
    data = form_fields or {}
    async with _acquire() as client:
        resp = await client.post(
            url,
            headers=_service_headers(ctx),
            files=files,
            data=data,
            timeout=UPLOAD_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
