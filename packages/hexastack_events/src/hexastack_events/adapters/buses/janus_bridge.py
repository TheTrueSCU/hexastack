"""Thread-safe asyncio-safe event and command queue bridge using janus.

Notes/Architectural Intent:
    ``janus`` provides a queue implementation that is simultaneously safe to use
    from synchronous OS threads (gRPC sync stubs, background worker threads, CLI
    handlers) and from ``asyncio`` coroutines sharing the same event loop.

    The bridge is designed to solve the hard problem of getting synchronous code
    (e.g. a gRPC servicer running in a ``ThreadPoolExecutor``) to publish events
    into an async event bus without directly running coroutines from non-async
    contexts.

    Pattern:
        - Sync producer thread calls ``sync_put()`` — this is a regular blocking
          put on the ``janus`` sync side.
        - The async drainer coroutine (``drain()``) runs perpetually on the event
          loop, pulling items from the async side and invoking the async handler.

    ``JanusCommandQueue[T]`` is a generic twin for command objects, enabling the
    same bridge pattern for CQRS command dispatch from synchronous contexts.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


def _require_janus() -> None:
    """Raise a helpful ImportError when janus is not installed.

    Raises:
        ImportError: Always, when the janus package is unavailable.

    Notes/Architectural Intent:
        Guards all runtime janus usage so that importing this module without the
        optional dependency installed gives a clear, actionable error message.
    """
    try:
        import janus  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "janus is required for JanusEventChannel and JanusCommandQueue. "
            "Install it with: pip install hexastack-events[janus]"
        ) from exc


class JanusEventChannel:
    """Thread-safe, asyncio-safe CloudEventEnvelope queue bridge.

    Notes/Architectural Intent:
        Wraps a ``janus.Queue[CloudEventEnvelope]`` to provide clean put/get
        semantics from both sync and async callers. Instantiation must happen
        inside a running asyncio event loop (e.g. within an async function or
        at application startup from an async context) because ``janus.Queue``
        binds to the current loop on construction.

    Example::

        async def start():
            channel = JanusEventChannel(maxsize=100)
            asyncio.create_task(channel.drain(my_async_handler))

            # In a gRPC thread:
            threading.Thread(
                target=lambda: channel.sync_put(my_envelope)
            ).start()
    """

    def __init__(self, maxsize: int = 0) -> None:
        """Initialise the janus queue.

        Args:
            maxsize: Maximum items held in the queue. ``0`` means unlimited.

        Raises:
            ImportError: If janus is not installed.

        Notes/Architectural Intent:
            Must be called from within a running asyncio event loop. The janus
            queue internally captures ``asyncio.get_event_loop()`` on construction.
        """
        _require_janus()
        import janus

        self._queue: janus.Queue = janus.Queue(maxsize=maxsize)

    async def async_put(self, envelope: object) -> None:
        """Enqueue an envelope from an async context.

        Args:
            envelope: CloudEventEnvelope (or any object) to enqueue.

        Notes/Architectural Intent:
            Awaits if the queue is full (when ``maxsize > 0``). Safe to call
            from any coroutine on the bound event loop.
        """
        await self._queue.async_q.put(envelope)

    def sync_put(self, envelope: object) -> None:
        """Enqueue an envelope from a synchronous thread.

        Args:
            envelope: CloudEventEnvelope (or any object) to enqueue.

        Notes/Architectural Intent:
            Blocks the calling thread if the queue is full. Designed for use by
            gRPC servicers or OS background threads that cannot await.
        """
        self._queue.sync_q.put(envelope)

    async def async_get(self) -> object:
        """Dequeue the next envelope from an async context.

        Returns:
            The next enqueued item.

        Notes/Architectural Intent:
            Awaits until an item is available. Typically used when you prefer
            manual control over ``drain()``.
        """
        return await self._queue.async_q.get()

    async def drain(self, handler: Callable[[Any], Awaitable[None]]) -> None:
        """Continuously drain the queue, passing each item to the async handler.

        Args:
            handler: Async callable invoked for each dequeued item.

        Notes/Architectural Intent:
            Runs indefinitely until cancelled via ``asyncio.CancelledError``. This
            is the recommended way to wire up the channel as a persistent consumer
            coroutine scheduled with ``asyncio.create_task()``.

            On cancellation the loop exits cleanly; any item currently being handled
            by the async handler finishes processing before the task terminates.
        """
        try:
            while True:
                item = await self._queue.async_q.get()
                await handler(item)
                self._queue.async_q.task_done()
        except asyncio.CancelledError:
            pass

    def close(self) -> None:
        """Close the underlying janus queue and release resources.

        Notes/Architectural Intent:
            Must be called during application shutdown to avoid resource warnings.
            After closing, both sync and async sides of the queue become unusable.
        """
        self._queue.close()


class JanusCommandQueue[T]:
    """Thread-safe, asyncio-safe generic command queue bridge.

    Notes/Architectural Intent:
        Typed twin of ``JanusEventChannel`` for CQRS command objects. Enables
        synchronous CLI handlers, gRPC stubs, or OS threads to enqueue commands
        that are dispatched by an async CQRS command bus running on the event loop.

        Generic parameter ``T`` is the command type (e.g. a Pydantic command model
        or a dataclass).

    Example::

        queue: JanusCommandQueue[CreateOrderCommand] = JanusCommandQueue()

        # In a sync gRPC handler:
        queue.sync_put(CreateOrderCommand(order_id="o-1"))

        # In async command dispatcher coroutine:
        cmd = await queue.async_get()
        await bus.dispatch(cmd)
    """

    def __init__(self, maxsize: int = 0) -> None:
        """Initialise the generic command queue.

        Args:
            maxsize: Maximum commands held. ``0`` means unlimited.

        Raises:
            ImportError: If janus is not installed.
        """
        _require_janus()
        import janus

        self._queue: janus.Queue[T] = janus.Queue(maxsize=maxsize)

    def sync_put(self, cmd: T) -> None:
        """Enqueue a command from a synchronous thread.

        Args:
            cmd: Command object to enqueue.
        """
        self._queue.sync_q.put(cmd)

    async def async_get(self) -> T:
        """Dequeue the next command from an async context.

        Returns:
            The next command object.
        """
        return await self._queue.async_q.get()

    async def drain(self, handler: Callable[[T], Awaitable[None]]) -> None:
        """Continuously drain and dispatch queued commands via the async handler.

        Args:
            handler: Async callable invoked with each command.

        Notes/Architectural Intent:
            Runs indefinitely until cancelled. Schedule with
            ``asyncio.create_task(queue.drain(bus.dispatch))``.
        """
        try:
            while True:
                cmd = await self._queue.async_q.get()
                await handler(cmd)
                self._queue.async_q.task_done()
        except asyncio.CancelledError:
            pass

    def close(self) -> None:
        """Close the queue and release resources."""
        self._queue.close()


__all__ = [
    "JanusCommandQueue",
    "JanusEventChannel",
]
