# backend/app/core/engine.py
import asyncio
from datetime import datetime
from typing import Callable, Dict, List
from collections import defaultdict

class Event:
    def __init__(self, event_type: str, data: dict):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now()

class EventEngine:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._queue = asyncio.Queue()
    
    def register(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self._handlers[event_type].append(handler)
    
    def unregister(self, event_type: str, handler: Callable):
        """注销事件处理器"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    async def put(self, event: Event):
        """放入事件"""
        await self._queue.put(event)
    
    async def _process(self):
        """处理事件"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                for handler in self._handlers.get(event.event_type, []):
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        print(f"Handler error: {e}")
            except asyncio.TimeoutError:
                continue
    
    def start(self):
        """启动引擎"""
        self._running = True
        asyncio.create_task(self._process())
    
    def stop(self):
        """停止引擎"""
        self._running = False