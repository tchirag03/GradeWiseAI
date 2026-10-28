"""
In-memory Event Bus for Real-Time Server-Sent Events (SSE).
Streams live evaluation pipeline events, stage transitions, and log messages
directly from Unified VLM and Worker to connected frontends.
"""
import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, List, Any

# Map of evaluation_id -> list of subscriber Queues
_subscribers: Dict[str, List[asyncio.Queue]] = {}

# In-memory history ring buffer per evaluation_id (last 100 events, max 50 evaluations)
_event_history: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()
MAX_HISTORY_PER_EVAL = 100
MAX_EVALUATIONS_BUFFERED = 50


async def subscribe_events(evaluation_id: str) -> asyncio.Queue:
    """Subscribes a new SSE client queue to an evaluation's stream."""
    queue: asyncio.Queue = asyncio.Queue()
    if evaluation_id not in _subscribers:
        _subscribers[evaluation_id] = []
    _subscribers[evaluation_id].append(queue)
    return queue


def unsubscribe_events(evaluation_id: str, queue: asyncio.Queue) -> None:
    """Removes a client queue on disconnect."""
    if evaluation_id in _subscribers:
        try:
            _subscribers[evaluation_id].remove(queue)
            if not _subscribers[evaluation_id]:
                del _subscribers[evaluation_id]
        except ValueError:
            pass


def get_history(evaluation_id: str) -> List[Dict[str, Any]]:
    """Returns buffered events so late-joining clients catch up immediately."""
    return list(_event_history.get(evaluation_id, []))


def clear_events(evaluation_id: str) -> None:
    """Free memory when an evaluation is deleted or finished."""
    _event_history.pop(evaluation_id, None)
    _subscribers.pop(evaluation_id, None)


async def publish_event(
    evaluation_id: str,
    event_type: str,
    message: str,
    data: Dict[str, Any] | None = None,
    level: str = "info",
) -> None:
    """
    Publishes an event to all active SSE subscribers for this evaluation.
    Also appends to the history buffer for late-connecting clients.
    Levels: 'info' | 'success' | 'warning' | 'error' | 'stage'
    """
    event = {
        "evaluation_id": evaluation_id,
        "type": event_type,
        "level": level,
        "message": message,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
    }

    # Store in history ring-buffer
    if evaluation_id not in _event_history:
        # Evict oldest evaluation if above capacity limit
        if len(_event_history) >= MAX_EVALUATIONS_BUFFERED:
            _event_history.popitem(last=False)
        _event_history[evaluation_id] = []
    else:
        _event_history.move_to_end(evaluation_id)

    _event_history[evaluation_id].append(event)
    if len(_event_history[evaluation_id]) > MAX_HISTORY_PER_EVAL:
        _event_history[evaluation_id].pop(0)

    # Dispatch to all active client queues
    queues = _subscribers.get(evaluation_id, [])
    for q in list(queues):
        try:
            q.put_nowait(event)
        except Exception:
            pass
