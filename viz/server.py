"""Visualization server — HTTP on :8080 for the page, WebSocket on :8765 for data.

The server also accepts incoming WebSocket messages from the browser:
  {"cmd": "toggle"}  — start or pause the simulation
"""
from __future__ import annotations
import asyncio
import http.server
import json
import multiprocessing as mp
import os
import pathlib
import sys
import threading
from typing import Optional, Set

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None  # type: ignore

VIZ_DIR = pathlib.Path(__file__).parent
HTTP_PORT = 8080
WS_PORT = 8765


def _start_http_server() -> None:
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a: None
    httpd = http.server.HTTPServer(("localhost", HTTP_PORT), handler)
    httpd.serve_forever()


async def _broadcast(clients: Set, message: str) -> None:
    if clients:
        await asyncio.gather(*[c.send(message) for c in clients], return_exceptions=True)


async def _ws_serve(queue: mp.Queue, run_event: Optional[mp.Event]) -> None:
    clients: Set[WebSocketServerProtocol] = set()

    async def handler(ws):
        clients.add(ws)
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    if msg.get("cmd") == "toggle" and run_event is not None:
                        if run_event.is_set():
                            run_event.clear()
                        else:
                            run_event.set()
                except Exception:
                    pass
        finally:
            clients.discard(ws)

    async with websockets.serve(handler, "localhost", WS_PORT):
        loop = asyncio.get_event_loop()
        while True:
            try:
                frame = await loop.run_in_executor(None, lambda: queue.get(timeout=0.05))
                await _broadcast(clients, json.dumps(frame))
            except Exception:
                await asyncio.sleep(0.01)


def run_server(queue: mp.Queue, run_event: Optional[mp.Event] = None) -> None:
    """Entry point called in a subprocess by the runner."""
    if websockets is None:
        print("[viz] websockets not installed — pip install websockets", file=sys.stderr)
        return

    os.chdir(VIZ_DIR)

    t = threading.Thread(target=_start_http_server, daemon=True)
    t.start()

    print(f"[viz] Open http://localhost:{HTTP_PORT} in your browser")
    asyncio.run(_ws_serve(queue, run_event))
