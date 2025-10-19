"""
Performance optimization utilities for the podcast generation system.

This module provides:
- In-memory caching with TTL support
- Request caching and deduplication
- Resource pooling and connection management
- Performance monitoring and metrics
- Background task management

Purpose: Optimize system performance and resource utilization.
"""

import time
import threading
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable, Union, Tuple, List
from functools import wraps
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, Future
import weakref

# Import configuration with fallback
try:
    from config import (
        PERFORMANCE_CONFIG, DEBUG, LOG_LEVEL,
        get_logger
    )
    logger = get_logger()
except ImportError:
    # Fallback for testing
    PERFORMANCE_CONFIG = type('Config', (), {
        'cache_enabled': True,
        'cache_timeout': 300,
        'thread_pool_workers': 4,
        'rate_limit_enabled': True,
        'rate_limit_requests': 10,
        'rate_limit_window': 300,
        'max_concurrent_generations': 5
    })()
    DEBUG = True
    LOG_LEVEL = 'INFO'
    import logging
    logger = logging.getLogger(__name__)


class TTLCache:
    """
    Time-based cache with TTL (Time To Live) support.

    Features:
    - Automatic expiration of cached items
    - Thread-safe operations
    - Memory-efficient storage with OrderedDict
    - Statistics tracking
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize TTL cache.

        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'expired': 0
        }

    def _is_expired(self, item: Tuple[Any, datetime]) -> bool:
        """Check if a cache item has expired."""
        _, expiry_time = item
        return datetime.now() > expiry_time

    def _cleanup_expired(self):
        """Remove expired items from cache."""
        expired_keys = []
        current_time = datetime.now()

        for key, (value, expiry_time) in self._cache.items():
            if current_time > expiry_time:
                expired_keys.append(key)
                self._stats['expired'] += 1

        for key in expired_keys:
            del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            value, expiry_time = self._cache[key]

            # Check if expired
            if datetime.now() > expiry_time:
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['expired'] += 1
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set item in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        with self._lock:
            # Calculate expiry time
            ttl = ttl if ttl is not None else self.default_ttl
            expiry_time = datetime.now() + timedelta(seconds=ttl)

            # Remove existing key if present
            if key in self._cache:
                del self._cache[key]

            # Add new item
            self._cache[key] = (value, expiry_time)
            self._stats['sets'] += 1

            # Enforce size limit (LRU eviction)
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1

    def delete(self, key: str) -> bool:
        """
        Delete item from cache.

        Args:
            key: Cache key

        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'evictions': 0,
                'expired': 0
            }

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            return {
                **self._stats,
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate_percent': round(hit_rate, 2),
                'total_requests': total_requests
            }


class RequestCache:
    """
    Cache for expensive function calls and API requests.

    Features:
    - Function result caching based on arguments
    - TTL support for cached results
    - Automatic cache key generation
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Initialize request cache.

        Args:
            max_size: Maximum number of cached requests
            default_ttl: Default TTL in seconds
        """
        self._cache = TTLCache(max_size, default_ttl)
        self._lock = threading.RLock()

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments."""
        # Create a deterministic key from function and arguments
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def cached(self, ttl: Optional[int] = None):
        """
        Decorator for caching function results.

        Args:
            ttl: TTL in seconds for cached results

        Returns:
            Decorated function with caching
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(func.__name__, args, kwargs)

                # Try to get from cache
                cached_result = self._cache.get(cache_key)
                if cached_result is not None:
                    if DEBUG:
                        logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result

                # Execute function
                if DEBUG:
                    logger.debug(f"Cache miss for {func.__name__}, executing...")

                result = func(*args, **kwargs)

                # Cache result
                self._cache.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()


class ResourcePool:
    """
    Generic resource pool for managing expensive resources.

    Features:
    - Resource creation and reuse
    - Maximum pool size limits
    - Resource health checking
    - Automatic cleanup of idle resources
    """

    def __init__(self, create_func: Callable, max_size: int = 10,
                 health_check: Optional[Callable] = None, max_idle_time: int = 300):
        """
        Initialize resource pool.

        Args:
            create_func: Function to create new resources
            max_size: Maximum pool size
            health_check: Optional function to check resource health
            max_idle_time: Maximum idle time before cleanup (seconds)
        """
        self.create_func = create_func
        self.max_size = max_size
        self.health_check = health_check
        self.max_idle_time = max_idle_time

        self._pool = []
        self._in_use = set()
        self._lock = threading.RLock()
        self._last_cleanup = time.time()

    def acquire(self) -> Any:
        """
        Acquire a resource from the pool.

        Returns:
            Resource instance
        """
        with self._lock:
            # Cleanup idle resources
            self._cleanup_idle()

            # Try to reuse existing resource
            while self._pool:
                resource = self._pool.pop()

                # Check health if health check function provided
                if self.health_check and not self.health_check(resource):
                    try:
                        # Try to cleanup unhealthy resource
                        if hasattr(resource, 'close'):
                            resource.close()
                    except Exception:
                        pass
                    continue

                self._in_use.add(resource)
                return resource

            # Create new resource if under max size
            if len(self._in_use) < self.max_size:
                resource = self.create_func()
                self._in_use.add(resource)
                return resource

            # Pool is full, raise exception
            raise RuntimeError("Resource pool exhausted")

    def release(self, resource: Any) -> None:
        """
        Release a resource back to the pool.

        Args:
            resource: Resource to release
        """
        with self._lock:
            if resource in self._in_use:
                self._in_use.remove(resource)

                # Add creation timestamp for tracking
                if not hasattr(resource, '_pool_created'):
                    resource._pool_created = time.time()

                self._pool.append(resource)
                # Sort by creation time (oldest first)
                self._pool.sort(key=lambda x: getattr(x, '_pool_created', 0))

    def _cleanup_idle(self) -> None:
        """Remove idle resources that have exceeded max idle time."""
        current_time = time.time()

        # Run cleanup periodically
        if current_time - self._last_cleanup < 60:  # Cleanup every minute
            return

        self._last_cleanup = current_time
        kept_resources = []

        for resource in self._pool:
            created_time = getattr(resource, '_pool_created', current_time)
            if current_time - created_time < self.max_idle_time:
                kept_resources.append(resource)
            else:
                try:
                    if hasattr(resource, 'close'):
                        resource.close()
                except Exception as e:
                    logger.warning(f"Error closing idle resource: {e}")

        self._pool = kept_resources

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'in_use': len(self._in_use),
                'max_size': self.max_size,
                'total_resources': len(self._pool) + len(self._in_use)
            }


class PerformanceMonitor:
    """
    Enhanced performance monitoring with metrics collection.

    Features:
    - Request timing and throughput monitoring
    - Resource usage tracking
    - Error rate monitoring
    - Performance alerting
    """

    def __init__(self):
        """Initialize performance monitor."""
        self._metrics = {
            'request_times': [],
            'request_count': 0,
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'start_time': datetime.now()
        }
        self._lock = threading.Lock()

    def record_request(self, duration: float, success: bool = True) -> None:
        """
        Record a request with timing and success status.

        Args:
            duration: Request duration in seconds
            success: Whether request was successful
        """
        with self._lock:
            self._metrics['request_times'].append(duration)
            self._metrics['request_count'] += 1

            if not success:
                self._metrics['error_count'] += 1

            # Keep only last 1000 request times
            if len(self._metrics['request_times']) > 1000:
                self._metrics['request_times'] = self._metrics['request_times'][-1000:]

    def record_request_with_metadata(self, duration: float, success: bool = True,
                                   operation_name: str = None,
                                   metadata: Dict[str, Any] = None) -> None:
        """
        Record a request with enhanced metadata and operation tracking.

        Args:
            duration: Request duration in seconds
            success: Whether request was successful
            operation_name: Name of the operation being performed
            metadata: Additional metadata about the operation
        """
        # Record basic request metrics
        self.record_request(duration, success)

        # Enhanced operation tracking (for future analytics)
        if not hasattr(self, '_operation_metrics'):
            self._operation_metrics = {}

        if operation_name:
            with self._lock:
                if operation_name not in self._operation_metrics:
                    self._operation_metrics[operation_name] = {
                        'count': 0,
                        'success_count': 0,
                        'total_duration': 0.0,
                        'min_duration': float('inf'),
                        'max_duration': 0.0,
                        'durations': []
                    }

                op_metrics = self._operation_metrics[operation_name]
                op_metrics['count'] += 1
                op_metrics['total_duration'] += duration
                op_metrics['min_duration'] = min(op_metrics['min_duration'], duration)
                op_metrics['max_duration'] = max(op_metrics['max_duration'], duration)
                op_metrics['durations'].append(duration)

                if success:
                    op_metrics['success_count'] += 1

                # Keep only last 100 durations per operation
                if len(op_metrics['durations']) > 100:
                    op_metrics['durations'] = op_metrics['durations'][-100:]

        # Log detailed metadata if provided (for debugging)
        if metadata and DEBUG:
            logger.debug(f"Performance metadata for {operation_name}: {metadata}")

    def get_operation_metrics(self, operation_name: str = None) -> Dict[str, Any]:
        """
        Get performance metrics for specific operations.

        Args:
            operation_name: Name of the operation (None for all operations)

        Returns:
            Dictionary containing operation performance metrics
        """
        if not hasattr(self, '_operation_metrics'):
            return {}

        with self._lock:
            if operation_name:
                if operation_name not in self._operation_metrics:
                    return {}

                op_metrics = self._operation_metrics[operation_name]
                durations = op_metrics['durations']

                if durations:
                    avg_duration = sum(durations) / len(durations)
                    sorted_durations = sorted(durations)
                    p50 = sorted_durations[len(sorted_durations) // 2]
                    p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
                    p99 = sorted_durations[int(len(sorted_durations) * 0.99)]
                else:
                    avg_duration = p50 = p95 = p99 = 0

                return {
                    'operation_name': operation_name,
                    'total_requests': op_metrics['count'],
                    'successful_requests': op_metrics['success_count'],
                    'success_rate_percent': (op_metrics['success_count'] / op_metrics['count'] * 100) if op_metrics['count'] > 0 else 0,
                    'avg_duration_seconds': round(avg_duration, 3),
                    'min_duration_seconds': round(op_metrics['min_duration'], 3),
                    'max_duration_seconds': round(op_metrics['max_duration'], 3),
                    'p50_duration_seconds': round(p50, 3),
                    'p95_duration_seconds': round(p95, 3),
                    'p99_duration_seconds': round(p99, 3)
                }
            else:
                # Return metrics for all operations
                all_metrics = {}
                for op_name in self._operation_metrics:
                    all_metrics[op_name] = self.get_operation_metrics(op_name)
                return all_metrics

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self._metrics['cache_hits'] += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self._metrics['cache_misses'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            request_times = self._metrics['request_times']

            if request_times:
                avg_time = sum(request_times) / len(request_times)
                max_time = max(request_times)
                min_time = min(request_times)

                # Calculate percentiles
                sorted_times = sorted(request_times)
                p50 = sorted_times[len(sorted_times) // 2]
                p95 = sorted_times[int(len(sorted_times) * 0.95)]
                p99 = sorted_times[int(len(sorted_times) * 0.99)]
            else:
                avg_time = max_time = min_time = p50 = p95 = p99 = 0

            total_requests = self._metrics['request_count']
            error_rate = (self._metrics['error_count'] / total_requests * 100) if total_requests > 0 else 0

            cache_total = self._metrics['cache_hits'] + self._metrics['cache_misses']
            cache_hit_rate = (self._metrics['cache_hits'] / cache_total * 100) if cache_total > 0 else 0

            uptime = datetime.now() - self._metrics['start_time']

            return {
                'request_metrics': {
                    'total_requests': total_requests,
                    'error_count': self._metrics['error_count'],
                    'error_rate_percent': round(error_rate, 2),
                    'avg_response_time': round(avg_time, 3),
                    'max_response_time': round(max_time, 3),
                    'min_response_time': round(min_time, 3),
                    'p50_response_time': round(p50, 3),
                    'p95_response_time': round(p95, 3),
                    'p99_response_time': round(p99, 3)
                },
                'cache_metrics': {
                    'hits': self._metrics['cache_hits'],
                    'misses': self._metrics['cache_misses'],
                    'hit_rate_percent': round(cache_hit_rate, 2)
                },
                'system_metrics': {
                    'uptime_seconds': uptime.total_seconds(),
                    'uptime_string': str(uptime).split('.')[0]
                }
            }


class BackgroundTaskManager:
    """
    Background task manager for async operations.

    Features:
    - Thread pool based task execution
    - Task status tracking
    - Result caching
    - Error handling and retry
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize background task manager.

        Args:
            max_workers: Maximum number of worker threads
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks = {}
        self._results = {}
        self._lock = threading.Lock()

    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> Future:
        """
        Submit a task for background execution.

        Args:
            task_id: Unique task identifier
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Future object for the task
        """
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task {task_id} already exists")

            future = self.executor.submit(func, *args, **kwargs)
            self._tasks[task_id] = future

            # Store result when complete
            def store_result(fut):
                try:
                    result = fut.result()
                    with self._lock:
                        self._results[task_id] = {
                            'result': result,
                            'completed_at': datetime.now(),
                            'success': True
                        }
                except Exception as e:
                    with self._lock:
                        self._results[task_id] = {
                            'error': str(e),
                            'completed_at': datetime.now(),
                            'success': False
                        }
                finally:
                    with self._lock:
                        self._tasks.pop(task_id, None)

            future.add_done_callback(store_result)
            return future

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a background task.

        Args:
            task_id: Task identifier

        Returns:
            Task status dict or None if not found
        """
        with self._lock:
            if task_id in self._tasks:
                future = self._tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': 'running' if not future.done() else 'completed',
                    'completed': future.done()
                }
            elif task_id in self._results:
                result = self._results[task_id].copy()
                result['task_id'] = task_id
                return result
            else:
                return None

    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get result of a completed task.

        Args:
            task_id: Task identifier
            timeout: Optional timeout for waiting

        Returns:
            Task result

        Raises:
            RuntimeError: If task not found or failed
            TimeoutError: If timeout exceeded
        """
        with self._lock:
            if task_id in self._tasks:
                future = self._tasks[task_id]
                result = future.result(timeout=timeout)
                return result
            elif task_id in self._results:
                result_data = self._results[task_id]
                if result_data['success']:
                    return result_data['result']
                else:
                    raise RuntimeError(f"Task failed: {result_data['error']}")
            else:
                raise RuntimeError(f"Task {task_id} not found")

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> None:
        """
        Clean up old completed tasks.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            # Clean up old results
            old_tasks = [
                task_id for task_id, result in self._results.items()
                if result['completed_at'] < cutoff_time
            ]

            for task_id in old_tasks:
                self._results.pop(task_id, None)

            if old_tasks:
                logger.debug(f"Cleaned up {len(old_tasks)} old background tasks")

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the task manager.

        Args:
            wait: Whether to wait for running tasks to complete
        """
        self.executor.shutdown(wait=wait)


# Global performance optimization instances
_request_cache = RequestCache(
    max_size=200 if PERFORMANCE_CONFIG.cache_enabled else 0,
    default_ttl=PERFORMANCE_CONFIG.cache_timeout
)

_performance_monitor = PerformanceMonitor()
_background_tasks = BackgroundTaskManager(max_workers=PERFORMANCE_CONFIG.thread_pool_workers)


def cached(ttl: Optional[int] = None):
    """
    Decorator for caching function results globally.

    Args:
        ttl: TTL in seconds

    Returns:
        Decorated function with caching
    """
    return _request_cache.cached(ttl=ttl)


def monitor_performance(operation_name: Optional[str] = None,
                      include_args: bool = False,
                      include_result: bool = False,
                      log_level: str = 'info',
                      enforce_nfrs: bool = True):
    """
    Enhanced performance monitoring decorator with NFR enforcement.

    Args:
        operation_name: Name of the operation (defaults to function name)
        include_args: Whether to include function arguments in metadata
        include_result: Whether to include function result in metadata
        log_level: Logging level for performance messages
        enforce_nfrs: Whether to enforce NFR performance requirements

    Returns:
        Decorated function with performance monitoring
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determine operation name
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            # Prepare metadata
            metadata = {
                'function_name': func.__name__,
                'module': func.__module__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            }

            if include_args:
                # Include safe representation of arguments (exclude sensitive data)
                safe_args = []
                for i, arg in enumerate(args):
                    if isinstance(arg, str) and len(arg) > 100:
                        safe_args.append(f"str({len(arg)} chars)")
                    else:
                        safe_args.append(repr(arg))
                metadata['args'] = safe_args

            # Start timing
            start_time = time.time()
            success = False
            result = None
            error = None

            try:
                # Execute the function
                result = func(*args, **kwargs)
                success = True

                if include_result:
                    # Include safe representation of result
                    if isinstance(result, str) and len(result) > 100:
                        metadata['result'] = f"str({len(result)} chars)"
                    else:
                        metadata['result'] = repr(result)

                return result

            except Exception as e:
                success = False
                error = str(e)
                metadata['error_type'] = type(e).__name__
                metadata['error_message'] = error

                # Log the exception
                logger.error(f"Exception in {op_name}: {error}", exc_info=True)

                raise

            finally:
                # End timing and record metric
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                # Record with enhanced performance monitor
                _performance_monitor.record_request_with_metadata(
                    duration=duration_ms / 1000,  # Convert to seconds
                    success=success,
                    operation_name=op_name,
                    metadata=metadata
                )

                # Enforce NFR requirements if enabled
                if enforce_nfrs:
                    _enforce_nfr_requirements(op_name, duration_ms, success)

                # Log performance if configured
                if log_level and hasattr(logger, log_level):
                    log_method = getattr(logger, log_level)
                    log_method(
                        f"Performance: {op_name} completed in {duration_ms:.2f}ms "
                        f"({'success' if success else 'failed'})"
                    )

        return wrapper
    return decorator


def monitor_async_performance(operation_name: Optional[str] = None,
                            include_args: bool = False,
                            include_result: bool = False,
                            log_level: str = 'info',
                            enforce_nfrs: bool = True):
    """
    Performance monitoring decorator for async functions with NFR enforcement.

    Args:
        operation_name: Name of the operation (defaults to function name)
        include_args: Whether to include function arguments in metadata
        include_result: Whether to include function result in metadata
        log_level: Logging level for performance messages
        enforce_nfrs: Whether to enforce NFR performance requirements

    Returns:
        Decorated async function with performance monitoring
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine operation name
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            # Prepare metadata
            metadata = {
                'function_name': func.__name__,
                'module': func.__module__,
                'is_async': True,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            }

            if include_args:
                safe_args = []
                for i, arg in enumerate(args):
                    if isinstance(arg, str) and len(arg) > 100:
                        safe_args.append(f"str({len(arg)} chars)")
                    else:
                        safe_args.append(repr(arg))
                metadata['args'] = safe_args

            # Start timing
            start_time = time.time()
            success = False
            result = None
            error = None

            try:
                # Execute the async function
                result = await func(*args, **kwargs)
                success = True

                if include_result:
                    if isinstance(result, str) and len(result) > 100:
                        metadata['result'] = f"str({len(result)} chars)"
                    else:
                        metadata['result'] = repr(result)

                return result

            except Exception as e:
                success = False
                error = str(e)
                metadata['error_type'] = type(e).__name__
                metadata['error_message'] = error

                # Log the exception
                logger.error(f"Exception in async {op_name}: {error}", exc_info=True)

                raise

            finally:
                # End timing and record metric
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                # Record with enhanced performance monitor
                _performance_monitor.record_request_with_metadata(
                    duration=duration_ms / 1000,  # Convert to seconds
                    success=success,
                    operation_name=op_name,
                    metadata=metadata
                )

                # Enforce NFR requirements if enabled
                if enforce_nfrs:
                    _enforce_nfr_requirements(op_name, duration_ms, success)

                # Log performance if configured
                if log_level and hasattr(logger, log_level):
                    log_method = getattr(logger, log_level)
                    log_method(
                        f"Performance: {op_name} completed in {duration_ms:.2f}ms "
                        f"({'success' if success else 'failed'})"
                    )

        return wrapper
    return decorator


def _enforce_nfr_requirements(operation_name: str, duration_ms: float, success: bool) -> None:
    """
    Enforce Non-Functional Requirements for performance.

    Args:
        operation_name: Name of the operation
        duration_ms: Duration in milliseconds
        success: Whether operation was successful
    """
    if not success:
        return  # Don't enforce NFRs for failed operations

    # Define NFR thresholds based on operation types
    nfr_thresholds = {
        # Configuration operations - NFR requirements
        'config_load': {
            'target_ms': 2000,    # 2-second load target
            'warning_ms': 2500,   # 2.5s warning
            'error_ms': 5000      # 5s error
        },
        'config_save': {
            'target_ms': 3000,    # 3-second save target
            'warning_ms': 4000,   # 4s warning
            'error_ms': 8000      # 8s error
        },
        'config_validate': {
            'target_ms': 2000,    # 2-second validation target
            'warning_ms': 3500,   # 3.5s warning
            'error_ms': 7000      # 7s error
        },

        # API operations
        'api_request': {
            'target_ms': 3000,
            'warning_ms': 5000,
            'error_ms': 10000
        },
        'api_validation': {
            'target_ms': 2000,
            'warning_ms': 4000,
            'error_ms': 8000
        },

        # Database operations
        'database_query': {
            'target_ms': 500,
            'warning_ms': 1000,
            'error_ms': 2000
        },
        'database_write': {
            'target_ms': 1000,
            'warning_ms': 1500,
            'error_ms': 3000
        },

        # Default thresholds for other operations
        'default': {
            'target_ms': 1000,
            'warning_ms': 2000,
            'error_ms': 5000
        }
    }

    # Determine which threshold to use
    threshold = nfr_thresholds.get('default')
    for key, thresh in nfr_thresholds.items():
        if key != 'default' and key in operation_name.lower():
            threshold = thresh
            break

    # Check performance against thresholds
    if duration_ms > threshold['error_ms']:
        logger.error(
            f"NFR VIOLATION - {operation_name}: "
            f"Duration {duration_ms:.2f}ms exceeds error threshold {threshold['error_ms']}ms"
        )
    elif duration_ms > threshold['warning_ms']:
        logger.warning(
            f"NFR WARNING - {operation_name}: "
            f"Duration {duration_ms:.2f}ms exceeds warning threshold {threshold['warning_ms']}ms"
        )
    elif duration_ms <= threshold['target_ms']:
        logger.debug(
            f"NFR TARGET MET - {operation_name}: "
            f"Duration {duration_ms:.2f}ms meets target threshold {threshold['target_ms']}ms"
        )


# Convenience functions for common operations with NFR enforcement
def monitor_config_operation(operation_type: str):
    """
    Monitor configuration-specific operations with NFR enforcement.

    Args:
        operation_type: Type of configuration operation (load, save, validate, etc.)
    """
    return monitor_performance(
        operation_name=f'config_{operation_type}',
        include_args=False,
        include_result=False,
        log_level='info',
        enforce_nfrs=True
    )


def monitor_api_operation(operation_type: str):
    """
    Monitor API-specific operations with NFR enforcement.

    Args:
        operation_type: Type of API operation (request, validation, etc.)
    """
    return monitor_performance(
        operation_name=f'api_{operation_type}',
        include_args=False,
        include_result=False,
        log_level='debug',
        enforce_nfrs=True
    )


def monitor_database_operation(operation_type: str):
    """
    Monitor database-specific operations with NFR enforcement.

    Args:
        operation_type: Type of database operation (query, write, etc.)
    """
    return monitor_performance(
        operation_name=f'database_{operation_type}',
        include_args=False,
        include_result=False,
        log_level='debug',
        enforce_nfrs=True
    )


# Backward compatibility - keep the original simple decorator
def legacy_monitor_performance(func: Callable) -> Callable:
    """
    Legacy performance monitoring decorator for backward compatibility.

    Args:
        func: Function to monitor

    Returns:
        Decorated function with performance monitoring
    """
    return monitor_performance(
        operation_name=f"{func.__module__}.{func.__name__}",
        enforce_nfrs=True,
        log_level='debug'
    )(func)


def get_performance_stats() -> Dict[str, Any]:
    """Get comprehensive performance statistics."""
    return {
        'cache_stats': _request_cache.get_stats(),
        'performance_metrics': _performance_monitor.get_metrics(),
        'background_tasks': {
            'active_tasks': len(_background_tasks._tasks),
            'completed_tasks': len(_background_tasks._results)
        }
    }


def cleanup_performance_data():
    """Clean up old performance data."""
    _background_tasks.cleanup_old_tasks()


# Initialize performance logging
logger.info("Performance optimization module initialized")
if PERFORMANCE_CONFIG.cache_enabled:
    logger.info(f"Request cache enabled (max_size=200, ttl={PERFORMANCE_CONFIG.cache_timeout}s)")
else:
    logger.info("Request cache disabled")