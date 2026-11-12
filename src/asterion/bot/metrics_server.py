"""`/metrics` server for the polling bot (B6), on aiohttp (already an aiogram dependency).

In webhook mode the FastAPI app serves `/metrics` instead. This server only
starts when `ASTERION_METRICS_PORT` is set.
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

from asterion.infrastructure.metrics import CONTENT_TYPE, authorized, render_metrics


def build_metrics_app(engine: Any, sessions: Any, token: str | None) -> web.Application:
    async def metrics(request: web.Request) -> web.Response:
        if not authorized(request.headers.get("Authorization"), token):
            return web.Response(status=401, text="unauthorized\n")
        body = await render_metrics(engine, sessions)
        return web.Response(body=body.encode(), headers={"Content-Type": CONTENT_TYPE})

    app = web.Application()
    app.router.add_get("/metrics", metrics)
    return app


async def start_metrics_server(
    engine: Any, sessions: Any, *, port: int, token: str | None, host: str = "0.0.0.0"
) -> web.AppRunner:
    runner = web.AppRunner(build_metrics_app(engine, sessions, token), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    return runner
