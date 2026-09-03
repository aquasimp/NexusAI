from __future__ import annotations
import asyncio, json
from collections import defaultdict


class Hub:
    """Minimal fan-out pub/sub for SSE. Slow consumers are dropped, never block."""

    def __init__(self, maxsize: int = 64):
        self.channels: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self.maxsize = maxsize

    def subscribe(self, channel: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self.maxsize)
        self.channels[channel].add(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        self.channels[channel].discard(q)

    async def publish(self, channel: str, event: str, data: dict) -> None:
        payload = f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        for q in list(self.channels[channel]):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                self.channels[channel].discard(q)


hub = Hub()
