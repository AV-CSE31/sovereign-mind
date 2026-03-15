"""
Module: Deep Observability (Tracing).

This module implements a local-first tracing system that mimics OpenTelemetry spans.
It allows capturing granular execution details (inputs, outputs, latency) for every agent node.
Traces are saved locally but structured for easy export to platforms like Langfuse or LangSmith.
"""

import asyncio
import functools
import json
import time
import uuid
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Context variables to track current trace and span
_current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)
_current_span_id: ContextVar[str | None] = ContextVar("current_span_id", default=None)


@dataclass
class Span:
    """Represents a single unit of work (e.g., a node execution)."""

    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start_time: float
    end_time: float = 0.0
    status: str = "running"  # running, success, error
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        if self.end_time == 0.0:
            return 0.0
        return (self.end_time - self.start_time) * 1000


class TraceManager:
    """Manages the lifecycle of traces and persists them."""

    def __init__(self, log_dir: str = "logs/traces", buffer_size: int = 1):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / "traces.jsonl"
        self.buffer = []
        self.buffer_size = buffer_size

    def start_trace(self, trace_id: str | None = None) -> str:
        """Start a new trace context."""
        tid = trace_id or str(uuid.uuid4())
        _current_trace_id.set(tid)
        return tid

    def start_span(self, name: str, inputs: dict[str, Any] | None = None) -> Span:
        """Start a new span within the current trace."""
        trace_id = _current_trace_id.get()
        if not trace_id:
            trace_id = self.start_trace()

        parent_id = _current_span_id.get()
        span_id = str(uuid.uuid4())

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            inputs=inputs or {},
        )

        # Set context for children
        _current_span_id.set(span_id)
        return span

    def end_span(self, span: Span, outputs: Any = None, error: Exception | None = None):
        """End a span and log it."""
        span.end_time = time.time()

        if error:
            span.status = "error"
            span.error = str(error)
        else:
            span.status = "success"
            if outputs:
                # Sanitize outputs (don't log huge objects if possible)
                # For now, simplistic logging
                if isinstance(outputs, dict):
                    span.outputs = outputs
                else:
                    span.outputs = {"result": str(outputs)}

        # Persist
        self._log_span(span)

        # Reset context (simplistic pop)
        _current_span_id.set(span.parent_id)

    def _json_serializer(self, obj):
        """Helper to serialize non-JSON objects."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "content"):  # LangChain Message
            return {"role": getattr(obj, "type", "unknown"), "content": obj.content}
        return str(obj)

    def _flush(self):
        """Write buffer to disk."""
        if not self.buffer:
            return

        try:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                for entry in self.buffer:
                    f.write(json.dumps(entry, default=self._json_serializer) + "\n")
            self.buffer = []
        except Exception as e:
            # Failsafe: don't crash the app if logging fails
            logger.error("trace_write_failed", error=str(e))
            self.buffer = []

    def _log_span(self, span: Span):
        """Add span to buffer and flush if buffer is full."""
        self.buffer.append(asdict(span))
        if len(self.buffer) >= self.buffer_size:
            self._flush()


# Singleton
_tracer = TraceManager()


def get_tracer() -> TraceManager:
    return _tracer


def trace_node(func):
    """Decorator to trace a LangGraph node execution."""

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()

            # Extract state from args if possible (usually first arg)
            inputs = {}
            if args:
                state_arg = args[0]
                if isinstance(state_arg, dict):
                    # sanitize state: just log keys or specific fields
                    inputs = {
                        k: v
                        for k, v in state_arg.items()
                        if k in ["query", "intent", "current_step"]
                    }

            span = tracer.start_span(name=func.__name__, inputs=inputs)

            try:
                result = await func(*args, **kwargs)
                tracer.end_span(span, outputs=result)
                return result
            except Exception as e:
                tracer.end_span(span, error=e)
                raise

        return wrapper
    else:

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            inputs = {}
            if args and isinstance(args[0], dict):
                inputs = {
                    k: v for k, v in args[0].items() if k in ["query", "intent", "current_step"]
                }

            span = tracer.start_span(name=func.__name__, inputs=inputs)

            try:
                result = func(*args, **kwargs)
                tracer.end_span(span, outputs=result)
                return result
            except Exception as e:
                tracer.end_span(span, error=e)
                raise

        return wrapper
