"""LLM token-usage instrumentation (M2 ops-hygiene).

Captures real prompt/completion token counts from every chat-completion call so
the ~95% gross-margin model can be validated against actual usage. Emitted as a
structured log line (`llm_usage ...`) that Railway aggregates; this single
`record_usage` seam is the place to later fan out to a metrics table if needed.

`surface` attributes the cost to a feature (tutor / coach / quiz / tips / …).
Callers set it with the `track()` context manager around their `.complete()`
call; unattributed calls log `surface=unknown` rather than failing.
"""
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import TypeVar

logger = logging.getLogger("llm.usage")

_surface: ContextVar[str] = ContextVar("llm_surface", default="unknown")


@contextmanager
def track(surface: str) -> Iterator[None]:
    """Attribute LLM usage recorded within this block to `surface`."""
    token = _surface.set(surface)
    try:
        yield
    finally:
        _surface.reset(token)


def current_surface() -> str:
    return _surface.get()


_T = TypeVar("_T")


def surface(name: str) -> Callable[[Callable[..., Awaitable[_T]]], Callable[..., Awaitable[_T]]]:
    """Decorator: attribute all LLM usage recorded inside an async function to
    `name`. Nests correctly — a decorated call inside another restores the outer
    surface on exit (e.g. moderation invoked within a coach turn)."""
    def decorator(fn: Callable[..., Awaitable[_T]]) -> Callable[..., Awaitable[_T]]:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> _T:
            with track(name):
                return await fn(*args, **kwargs)
        return wrapper
    return decorator


def record_usage(
    *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
) -> None:
    """Record one completion's token usage. Never raises — telemetry must not
    break an LLM response."""
    try:
        total = (prompt_tokens or 0) + (completion_tokens or 0)
        logger.info(
            "llm_usage surface=%s provider=%s model=%s prompt_tokens=%d "
            "completion_tokens=%d total_tokens=%d",
            _surface.get(), provider, model, prompt_tokens or 0, completion_tokens or 0, total,
        )
    except Exception:  # pragma: no cover - telemetry must never propagate
        logger.debug("llm_usage record failed", exc_info=True)
