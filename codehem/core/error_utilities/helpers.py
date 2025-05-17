"""Utility classes and decorators used in tests.

This module provides simplified implementations of several helper
constructs that were available in earlier versions of CodeHem.
They are sufficient for the unit tests in this repository.
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar

from codehem.core.error_handling import CodeHemError, ValidationError

T = TypeVar("T")


# ===== Logging utilities =====
class ErrorLogFormatter:
    """Utility for formatting exceptions."""

    @staticmethod
    def format_basic(error: Exception) -> str:
        return f"{type(error).__name__}: {error}"

    @staticmethod
    def format_with_context(error: Exception) -> str:
        if isinstance(error, CodeHemError) and getattr(error, "context", None):
            ctx = ", ".join(f"{k}={v}" for k, v in error.context.items())
            return f"{type(error).__name__}: {error.message} [{ctx}]"
        return ErrorLogFormatter.format_basic(error)

    @staticmethod
    def format_with_trace(error: Exception, limit: int = 10) -> str:
        if not getattr(error, "__traceback__", None):
            return ErrorLogFormatter.format_with_context(error)
        import traceback

        tb = "".join(traceback.format_tb(error.__traceback__, limit=limit))
        return f"{ErrorLogFormatter.format_with_context(error)}\n\nTraceback:\n{tb}"


class ErrorLogger:
    """Small wrapper around :mod:`logging` used in tests."""

    def __init__(self, logger_name: str = "codehem") -> None:
        self.logger = logging.getLogger(logger_name)

    def _log(self, level: int, message: str, error: Optional[Exception], include_trace: bool) -> None:
        if error:
            if include_trace:
                message = f"{message}\n{ErrorLogFormatter.format_with_trace(error)}"
            else:
                message = f"{message}: {ErrorLogFormatter.format_with_context(error)}"
        self.logger.log(level, message)

    def debug(self, message: str, error: Optional[Exception] = None, include_trace: bool = False) -> None:
        self._log(logging.DEBUG, message, error, include_trace)

    def info(self, message: str, error: Optional[Exception] = None) -> None:
        self._log(logging.INFO, message, error, False)

    def warning(self, message: str, error: Optional[Exception] = None, include_trace: bool = False) -> None:
        self._log(logging.WARNING, message, error, include_trace)

    def error(self, message: str, error: Optional[Exception] = None, include_trace: bool = True) -> None:
        self._log(logging.ERROR, message, error, include_trace)

    def critical(self, message: str, error: Optional[Exception] = None, include_trace: bool = True) -> None:
        self._log(logging.CRITICAL, message, error, include_trace)

    def log_exception(self, error: Exception, level: int = logging.ERROR, message: Optional[str] = None, include_trace: bool = True) -> None:
        self._log(level, message or str(error), error, include_trace)


error_logger = ErrorLogger()


def log_error(message: str, error: Optional[Exception] = None, level: int = logging.ERROR, include_trace: bool = True, logger: Optional[logging.Logger] = None) -> None:
    custom = ErrorLogger(logger.name) if logger else error_logger
    custom.log_exception(error, level, message, include_trace) if error else custom.debug(message)


def log_errors(func: Callable[..., T]) -> Callable[..., T]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_error(f"Error in {func.__name__}", e, logging.ERROR, True)
            raise

    return wrapper


# ===== Graceful degradation utilities =====
class CircuitBreakerError(Exception):
    """Raised when a circuit breaker blocks execution."""


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    @property
    def state(self) -> str:
        if self._state == self.OPEN and (time.time() - self.last_failure_time >= self.recovery_timeout):
            self._state = self.HALF_OPEN
        return self._state

    def execute(self, func: Callable[[], T]) -> T:
        if self.state == self.OPEN:
            raise CircuitBreakerError("Circuit open")
        try:
            result = func()
        except Exception:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self._state = self.OPEN
            raise
        else:
            if self.state == self.HALF_OPEN:
                self.reset()
            return result

    def reset(self) -> None:
        self._state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0


def fallback(backup_function: Callable[..., T], exceptions: Tuple[Type[Exception], ...] = (Exception,), log_errors: bool = True, logger: Optional[logging.Logger] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    log_error(f"Function {func.__name__} failed", e, logging.WARNING, True, logger)
                return backup_function(*args, **kwargs)

        return wrapper

    return decorator


class FeatureFlags:
    def __init__(self) -> None:
        self._flags: Dict[str, bool] = {}
        self._defaults: Dict[str, bool] = {}

    def register(self, flag_name: str, default_value: bool = True) -> None:
        self._defaults[flag_name] = default_value
        self._flags.setdefault(flag_name, default_value)

    def enable(self, flag_name: str) -> None:
        self._flags[flag_name] = True

    def disable(self, flag_name: str) -> None:
        self._flags[flag_name] = False

    def is_enabled(self, flag_name: str) -> bool:
        return self._flags.get(flag_name, self._defaults.get(flag_name, False))

    def reset_all(self) -> None:
        for k, v in self._defaults.items():
            self._flags[k] = v


feature_flags = FeatureFlags()


def with_feature_flag(flag_name: str, default_behavior: bool = True) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        feature_flags.register(flag_name, default_behavior)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            if feature_flags.is_enabled(flag_name):
                return func(*args, **kwargs)
            return kwargs.pop("fallback_value", None)

        return wrapper

    return decorator


# ===== Exception conversion utilities =====
class ExceptionMapper:
    def __init__(self) -> None:
        self._mapping: Dict[Type[Exception], Tuple[Type[Exception], Optional[str], Dict[str, str]]] = {}

    def register(self, source_exception: Type[Exception], target_exception: Type[Exception], message_template: Optional[str] = None, context_mapping: Optional[Dict[str, str]] = None) -> None:
        self._mapping[source_exception] = (target_exception, message_template, context_mapping or {})

    def convert(self, exception: Exception) -> Exception:
        exc_type = type(exception)
        for source, (target, template, context_map) in self._mapping.items():
            if isinstance(exception, source):
                message = template.format(original=str(exception)) if template else str(exception)
                if issubclass(target, CodeHemError):
                    context = {k: getattr(exception, src, None) for src, k in context_map.items()}
                    return target(message, **context)
                return target(message)
        return exception

    def wrap(self, func: Callable[..., T], *source_exceptions: Type[Exception]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if source_exceptions and not isinstance(e, source_exceptions):
                    raise
                converted = self.convert(e)
                if converted is e:
                    raise
                raise converted from e

        return wrapper


def convert_exception(exception: Exception, target_exception: Type[Exception], message: Optional[str] = None, **context: Any) -> Exception:
    msg = message or str(exception)
    if issubclass(target_exception, CodeHemError):
        new_exc = target_exception(msg, **context)
    else:
        new_exc = target_exception(msg)
    new_exc.__cause__ = exception
    return new_exc


def map_exception(source_exception: Type[Exception], target_exception: Type[Exception], message_template: Optional[str] = None, context_mapping: Optional[Dict[str, str]] = None) -> None:
    global _default_mapper
    _default_mapper.register(source_exception, target_exception, message_template, context_mapping)


_default_mapper = ExceptionMapper()


def catching(*exception_types: Type[Exception], reraise_as: Optional[Type[Exception]] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                if reraise_as is not None:
                    converted = convert_exception(e, reraise_as, f"Error in {func.__name__}")
                    raise converted from e
                raise

        return wrapper

    return decorator

