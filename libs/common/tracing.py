from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

TRACE_ID_CTX: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    trace_id = TRACE_ID_CTX.get()
    if trace_id:
        return trace_id
    new_trace = uuid4().hex
    TRACE_ID_CTX.set(new_trace)
    return new_trace


def set_trace_id(trace_id: str) -> None:
    TRACE_ID_CTX.set(trace_id)
