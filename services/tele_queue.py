"""
TeleQueue: Message queue with rate limiting and retry logic
"""
import asyncio
import random
import logging
from typing import Callable, Awaitable, Dict
from collections import defaultdict

logger = logging.getLogger("SysAlertBot.tele_queue")


class TeleQueue:
    """Async message queue with rate limiting"""
    
    def __init__(
        self,
        bot_send: Callable[..., Awaitable],
        workers: int = 3,
        per_chat_rate_seconds: float = 1.0,
        max_attempts: int = 5
    ):
        self._q = asyncio.Queue()
        self._workers = workers
        self._bot_send = bot_send
        self._tasks = []
        self._running = False
        self._per_chat_rate_seconds = per_chat_rate_seconds
        self._max_attempts = max_attempts
        self._last_sent: Dict[int, float] = {}
        self._stats = {"sent": 0, "failed": 0, "dropped": 0}
    
    async def start(self):
        """Start worker tasks"""
        if self._running:
            return
        
        self._running = True
        for i in range(self._workers):
            task = asyncio.create_task(self._worker(i))
            self._tasks.append(task)
        
        logger.info(f"TeleQueue started with {self._workers} workers")
    
    async def stop(self):
        """Stop workers gracefully"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("TeleQueue stopped")
    
    async def enqueue(self, chat_id: int, text: str):
        """Add message to queue"""
        await self._q.put({"chat_id": chat_id, "text": text, "attempts": 0})
    
    def queue_size(self) -> int:
        return self._q.qsize()
    
    def get_stats(self) -> Dict[str, int]:
        return self._stats.copy()
    
    async def _worker(self, worker_id: int):
        """Worker task"""
        while self._running:
            try:
                item = await asyncio.wait_for(self._q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            try:
                await self._send_with_backoff(item, worker_id)
            except Exception:
                logger.exception(f"Worker {worker_id}: Error processing item")
            finally:
                try:
                    self._q.task_done()
                except:
                    pass
    
    async def _send_with_backoff(self, item: Dict, worker_id: int):
        """Send with exponential backoff"""
        chat_id = item["chat_id"]
        text = item["text"]
        
        while item["attempts"] < self._max_attempts:
            # Rate limiting
            now = asyncio.get_event_loop().time()
            last_sent = self._last_sent.get(chat_id, 0)
            wait_time = max(0, self._per_chat_rate_seconds - (now - last_sent))
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            try:
                await self._bot_send(chat_id=chat_id, text=text)
                self._last_sent[chat_id] = asyncio.get_event_loop().time()
                self._stats["sent"] += 1
                return
            except Exception as e:
                item["attempts"] += 1
                self._stats["failed"] += 1
                
                delay = min(60, (2 ** (item["attempts"] - 1)) + random.uniform(0, 0.5))
                
                logger.warning(
                    f"Worker {worker_id}: Failed to send to {chat_id} "
                    f"(attempt {item['attempts']}/{self._max_attempts}). "
                    f"Retrying in {delay:.1f}s"
                )
                
                if item["attempts"] < self._max_attempts:
                    await asyncio.sleep(delay)
        
        self._stats["dropped"] += 1
        logger.error(f"Worker {worker_id}: Dropped message to {chat_id}")