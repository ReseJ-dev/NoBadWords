"""Thread-safe cooperative cancellation primitives."""

from collections.abc import Callable
import threading


class OperationCancelled(RuntimeError):
    """Raised when a background operation is cancelled by the user."""


class CancellationToken:
    """Share cancellation state and callbacks safely across threads."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        if self._event.is_set():
            return
        self._event.set()
        with self._lock:
            callbacks = tuple(self._callbacks)
        for callback in callbacks:
            callback()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise OperationCancelled("Operation cancelled by the user.")

    def add_callback(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if not self._event.is_set():
                self._callbacks.append(callback)
                return
        callback()

    def remove_callback(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

