"""
Rate Limiting and Abuse Prevention Module

Provides session-based rate limiting with sliding window algorithm to prevent
abuse and enforce security requirements. Supports different rate limits for
different operations and includes comprehensive monitoring and logging.

Features:
- Session-based rate limiting with sliding window
- Memory-based storage for high performance
- Configurable rate limits per operation
- Comprehensive monitoring and alerting
- Automatic cleanup of expired sessions
- Support for multiple rate limit strategies
"""

import time
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps

# Import configuration with fallback
try:
    from config import DEBUG, LOG_LEVEL, get_logger
    logger = get_logger()
except ImportError:
    # Fallback for testing
    DEBUG = True
    LOG_LEVEL = 'INFO'
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """
    Rate limit rule configuration.
    """
    operation_name: str
    max_requests: int
    window_seconds: int
    strategy: str = 'sliding_window'  # sliding_window, fixed_window, token_bucket
    description: str = ""

    def __post_init__(self):
        """Validate rule parameters."""
        if self.max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.strategy not in ['sliding_window', 'fixed_window', 'token_bucket']:
            raise ValueError("strategy must be one of: sliding_window, fixed_window, token_bucket")


@dataclass
class RateLimitResult:
    """
    Result of a rate limit check.
    """
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    current_usage: int
    max_requests: int
    window_seconds: int
    retry_after: Optional[int] = None
    session_id: str = ""
    operation_name: str = ""


class SessionTracker:
    """
    Tracks rate limiting data for individual sessions.
    """

    def __init__(self, session_id: str, rule: RateLimitRule):
        """
        Initialize session tracker.

        Args:
            session_id: Unique session identifier
            rule: Rate limit rule to apply
        """
        self.session_id = session_id
        self.rule = rule
        self.created_at = datetime.now()
        self.last_access = datetime.now()

        # Strategy-specific storage
        if rule.strategy == 'sliding_window':
            self.request_times = deque()
        elif rule.strategy == 'fixed_window':
            self.current_window_start = datetime.now()
            self.request_count = 0
        elif rule.strategy == 'token_bucket':
            self.tokens = rule.max_requests
            self.last_refill = datetime.now()

    def is_expired(self, max_age_minutes: int = 60) -> bool:
        """
        Check if session tracker has expired.

        Args:
            max_age_minutes: Maximum age in minutes

        Returns:
            True if expired, False otherwise
        """
        return datetime.now() - self.last_access > timedelta(minutes=max_age_minutes)

    def update_access(self):
        """Update last access time."""
        self.last_access = datetime.now()


class RateLimiter:
    """
    Central rate limiting system with multiple strategies and session tracking.
    """

    def __init__(self, cleanup_interval: int = 300, max_sessions: int = 10000):
        """
        Initialize rate limiter.

        Args:
            cleanup_interval: Interval in seconds for cleanup
            max_sessions: Maximum number of sessions to track
        """
        self.cleanup_interval = cleanup_interval
        self.max_sessions = max_sessions

        # Thread-safe storage
        self._lock = threading.RLock()
        self._sessions: Dict[str, Dict[str, SessionTracker]] = defaultdict(dict)
        self._rules: Dict[str, RateLimitRule] = {}
        self._last_cleanup = time.time()

        # Statistics
        self._stats = {
            'total_checks': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'sessions_created': 0,
            'sessions_expired': 0,
            'rule_violations': defaultdict(int)
        }

        # Setup default rules
        self._setup_default_rules()

        logger.info(f"Rate limiter initialized with {len(self._rules)} default rules")

    def _setup_default_rules(self):
        """Setup default rate limiting rules."""
        default_rules = {
            # Configuration operations - 5 requests per minute (Security NFR)
            'config_load': RateLimitRule(
                operation_name='config_load',
                max_requests=5,
                window_seconds=60,
                strategy='sliding_window',
                description="Configuration loading operations"
            ),
            'config_save': RateLimitRule(
                operation_name='config_save',
                max_requests=5,
                window_seconds=60,
                strategy='sliding_window',
                description="Configuration saving operations"
            ),
            'config_validate': RateLimitRule(
                operation_name='config_validate',
                max_requests=10,
                window_seconds=60,
                strategy='sliding_window',
                description="API key validation operations"
            ),
            'config_export': RateLimitRule(
                operation_name='config_export',
                max_requests=3,
                window_seconds=60,
                strategy='sliding_window',
                description="Configuration export operations"
            ),
            'config_import': RateLimitRule(
                operation_name='config_import',
                max_requests=3,
                window_seconds=60,
                strategy='sliding_window',
                description="Configuration import operations"
            ),

            # API operations
            'api_request': RateLimitRule(
                operation_name='api_request',
                max_requests=20,
                window_seconds=60,
                strategy='sliding_window',
                description="General API requests"
            ),
            'api_validation': RateLimitRule(
                operation_name='api_validation',
                max_requests=10,
                window_seconds=60,
                strategy='sliding_window',
                description="API validation requests"
            ),

            # Database operations
            'database_query': RateLimitRule(
                operation_name='database_query',
                max_requests=100,
                window_seconds=60,
                strategy='sliding_window',
                description="Database query operations"
            ),
            'database_write': RateLimitRule(
                operation_name='database_write',
                max_requests=50,
                window_seconds=60,
                strategy='sliding_window',
                description="Database write operations"
            ),

            # Default rule for unspecified operations
            'default': RateLimitRule(
                operation_name='default',
                max_requests=10,
                window_seconds=60,
                strategy='sliding_window',
                description="Default rate limit for unspecified operations"
            )
        }

        for rule in default_rules.values():
            self.add_rule(rule)

    def add_rule(self, rule: RateLimitRule):
        """
        Add a rate limiting rule.

        Args:
            rule: Rate limit rule to add
        """
        with self._lock:
            self._rules[rule.operation_name] = rule
            logger.info(f"Added rate limit rule for {rule.operation_name}: "
                       f"{rule.max_requests} requests per {rule.window_seconds} seconds")

    def get_rule(self, operation_name: str) -> Optional[RateLimitRule]:
        """
        Get rate limit rule for an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Rate limit rule if found, None otherwise
        """
        # Direct match first
        if operation_name in self._rules:
            return self._rules[operation_name]

        # Fuzzy matching for operation types
        for key, rule in self._rules.items():
            if key != 'default' and key in operation_name.lower():
                return rule

        # Default rule
        return self._rules.get('default')

    def check_rate_limit(self, session_id: str, operation_name: str) -> RateLimitResult:
        """
        Check if a request is allowed based on rate limits.

        Args:
            session_id: Unique session identifier
            operation_name: Name of the operation

        Returns:
            Rate limit result
        """
        with self._lock:
            self._stats['total_checks'] += 1

            # Cleanup expired sessions periodically
            self._cleanup_expired_sessions()

            # Get applicable rule
            rule = self.get_rule(operation_name)
            if not rule:
                logger.warning(f"No rate limit rule found for operation: {operation_name}")
                # Allow request but log warning
                return RateLimitResult(
                    allowed=True,
                    remaining_requests=999,
                    reset_time=datetime.now() + timedelta(seconds=60),
                    current_usage=0,
                    max_requests=999,
                    window_seconds=60,
                    session_id=session_id,
                    operation_name=operation_name
                )

            # Get or create session tracker
            operation_sessions = self._sessions[operation_name]
            if session_id not in operation_sessions:
                operation_sessions[session_id] = SessionTracker(session_id, rule)
                self._stats['sessions_created'] += 1
                if DEBUG:
                    logger.debug(f"Created new rate limit session for {operation_name}: {session_id}")

            tracker = operation_sessions[session_id]
            tracker.update_access()

            # Check rate limit based on strategy
            if rule.strategy == 'sliding_window':
                result = self._check_sliding_window(tracker)
            elif rule.strategy == 'fixed_window':
                result = self._check_fixed_window(tracker)
            elif rule.strategy == 'token_bucket':
                result = self._check_token_bucket(tracker)
            else:
                logger.error(f"Unknown rate limit strategy: {rule.strategy}")
                result = RateLimitResult(
                    allowed=True,
                    remaining_requests=rule.max_requests,
                    reset_time=datetime.now() + timedelta(seconds=rule.window_seconds),
                    current_usage=0,
                    max_requests=rule.max_requests,
                    window_seconds=rule.window_seconds,
                    session_id=session_id,
                    operation_name=operation_name
                )

            # Update statistics
            if result.allowed:
                self._stats['allowed_requests'] += 1
            else:
                self._stats['blocked_requests'] += 1
                self._stats['rule_violations'][operation_name] += 1
                logger.warning(f"Rate limit exceeded for {operation_name} "
                             f"session {session_id}: {result.current_usage}/{result.max_requests}")

            return result

    def _check_sliding_window(self, tracker: SessionTracker) -> RateLimitResult:
        """
        Check rate limit using sliding window algorithm.

        Args:
            tracker: Session tracker for the session

        Returns:
            Rate limit result
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=tracker.rule.window_seconds)

        # Remove old requests outside the window
        while tracker.request_times and tracker.request_times[0] < window_start:
            tracker.request_times.popleft()

        # Check if under limit
        if len(tracker.request_times) < tracker.rule.max_requests:
            # Add current request
            tracker.request_times.append(now)

            return RateLimitResult(
                allowed=True,
                remaining_requests=tracker.rule.max_requests - len(tracker.request_times),
                reset_time=now + timedelta(seconds=tracker.rule.window_seconds),
                current_usage=len(tracker.request_times),
                max_requests=tracker.rule.max_requests,
                window_seconds=tracker.rule.window_seconds,
                session_id=tracker.session_id,
                operation_name=tracker.rule.operation_name
            )
        else:
            # Rate limit exceeded
            oldest_request = tracker.request_times[0]
            reset_time = oldest_request + timedelta(seconds=tracker.rule.window_seconds)
            retry_after = max(1, int((reset_time - now).total_seconds()))

            return RateLimitResult(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                current_usage=len(tracker.request_times),
                max_requests=tracker.rule.max_requests,
                window_seconds=tracker.rule.window_seconds,
                retry_after=retry_after,
                session_id=tracker.session_id,
                operation_name=tracker.rule.operation_name
            )

    def _check_fixed_window(self, tracker: SessionTracker) -> RateLimitResult:
        """
        Check rate limit using fixed window algorithm.

        Args:
            tracker: Session tracker for the session

        Returns:
            Rate limit result
        """
        now = datetime.now()

        # Check if we need to reset the window
        if now - tracker.current_window_start >= timedelta(seconds=tracker.rule.window_seconds):
            tracker.current_window_start = now
            tracker.request_count = 0

        # Check if under limit
        if tracker.request_count < tracker.rule.max_requests:
            tracker.request_count += 1

            return RateLimitResult(
                allowed=True,
                remaining_requests=tracker.rule.max_requests - tracker.request_count,
                reset_time=tracker.current_window_start + timedelta(seconds=tracker.rule.window_seconds),
                current_usage=tracker.request_count,
                max_requests=tracker.rule.max_requests,
                window_seconds=tracker.rule.window_seconds,
                session_id=tracker.session_id,
                operation_name=tracker.rule.operation_name
            )
        else:
            # Rate limit exceeded
            reset_time = tracker.current_window_start + timedelta(seconds=tracker.rule.window_seconds)
            retry_after = max(1, int((reset_time - now).total_seconds()))

            return RateLimitResult(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                current_usage=tracker.request_count,
                max_requests=tracker.rule.max_requests,
                window_seconds=tracker.rule.window_seconds,
                retry_after=retry_after,
                session_id=tracker.session_id,
                operation_name=tracker.rule.operation_name
            )

    def _check_token_bucket(self, tracker: SessionTracker) -> RateLimitResult:
        """
        Check rate limit using token bucket algorithm.

        Args:
            tracker: Session tracker for the session

        Returns:
            Rate limit result
        """
        now = datetime.now()

        # Refill tokens based on time elapsed
        time_elapsed = (now - tracker.last_refill).total_seconds()
        tokens_to_add = (time_elapsed / tracker.rule.window_seconds) * tracker.rule.max_requests

        tracker.tokens = min(tracker.rule.max_requests, tracker.tokens + tokens_to_add)
        tracker.last_refill = now

        # Check if we have enough tokens
        if tracker.tokens >= 1:
            tracker.tokens -= 1

            return RateLimitResult(
                allowed=True,
                remaining_requests=int(tracker.tokens),
                reset_time=now + timedelta(seconds=tracker.rule.window_seconds),
                current_usage=tracker.rule.max_requests - int(tracker.tokens),
                max_requests=tracker.rule.max_requests,
                window_seconds=tracker.rule.window_seconds,
                session_id=tracker.session_id,
                operation_name=tracker.rule.operation_name
            )
        else:
            # Rate limit exceeded
            time_to_refill = (1 - tracker.tokens) * tracker.rule.window_seconds / tracker.rule.max_requests
            reset_time = now + timedelta(seconds=time_to_refill)
            retry_after = max(1, int(time_to_refill))

            return RateLimitResult(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                current_usage=tracker.rule.max_requests,
                max_requests=tracker.rule.max_requests,
                window_seconds=tracker.rule.window_seconds,
                retry_after=retry_after,
                session_id=tracker.session_id,
                operation_name=tracker.rule.operation_name
            )

    def _cleanup_expired_sessions(self):
        """Clean up expired sessions to prevent memory leaks."""
        current_time = time.time()

        # Run cleanup periodically
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = current_time
        total_expired = 0

        for operation_name in list(self._sessions.keys()):
            operation_sessions = self._sessions[operation_name]
            expired_sessions = []

            for session_id, tracker in operation_sessions.items():
                if tracker.is_expired():
                    expired_sessions.append(session_id)

            # Remove expired sessions
            for session_id in expired_sessions:
                del operation_sessions[session_id]
                total_expired += 1

            # Remove empty operation dictionaries
            if not operation_sessions:
                del self._sessions[operation_name]

        # Enforce maximum session limit
        if len(self._get_all_sessions()) > self.max_sessions:
            self._enforce_session_limit()

        if total_expired > 0:
            self._stats['sessions_expired'] += total_expired
            logger.debug(f"Cleaned up {total_expired} expired rate limit sessions")

    def _get_all_sessions(self) -> List[Tuple[str, str]]:
        """Get all sessions as (operation_name, session_id) tuples."""
        all_sessions = []
        for operation_name, operation_sessions in self._sessions.items():
            for session_id in operation_sessions:
                all_sessions.append((operation_name, session_id))
        return all_sessions

    def _enforce_session_limit(self):
        """Enforce maximum session limit by removing oldest sessions."""
        all_sessions = self._get_all_sessions()

        if len(all_sessions) <= self.max_sessions:
            return

        # Sort by last access time (oldest first)
        sessions_with_time = []
        for operation_name, session_id in all_sessions:
            tracker = self._sessions[operation_name][session_id]
            sessions_with_time.append((tracker.last_access, operation_name, session_id))

        sessions_with_time.sort()

        # Remove oldest sessions
        to_remove = len(all_sessions) - self.max_sessions + 100  # Remove extra to avoid frequent cleanup
        for i in range(min(to_remove, len(sessions_with_time))):
            _, operation_name, session_id = sessions_with_time[i]
            del self._sessions[operation_name][session_id]

            # Remove empty operation dictionaries
            if not self._sessions[operation_name]:
                del self._sessions[operation_name]

        logger.warning(f"Removed {to_remove} oldest rate limit sessions to enforce limit")

    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        with self._lock:
            total_sessions = sum(len(sessions) for sessions in self._sessions.values())

            return {
                'total_checks': self._stats['total_checks'],
                'allowed_requests': self._stats['allowed_requests'],
                'blocked_requests': self._stats['blocked_requests'],
                'sessions_created': self._stats['sessions_created'],
                'sessions_expired': self._stats['sessions_expired'],
                'active_sessions': total_sessions,
                'max_sessions': self.max_sessions,
                'block_rate_percent': round(
                    (self._stats['blocked_requests'] / self._stats['total_checks'] * 100)
                    if self._stats['total_checks'] > 0 else 0, 2
                ),
                'rule_violations': dict(self._stats['rule_violations']),
                'configured_rules': {
                    name: {
                        'max_requests': rule.max_requests,
                        'window_seconds': rule.window_seconds,
                        'strategy': rule.strategy,
                        'description': rule.description
                    }
                    for name, rule in self._rules.items()
                },
                'last_cleanup': datetime.fromtimestamp(self._last_cleanup).isoformat()
            }

    def reset_session(self, session_id: str, operation_name: str = None):
        """
        Reset rate limit for a specific session.

        Args:
            session_id: Session identifier to reset
            operation_name: Specific operation to reset (None for all operations)
        """
        with self._lock:
            if operation_name:
                if operation_name in self._sessions and session_id in self._sessions[operation_name]:
                    del self._sessions[operation_name][session_id]
                    logger.info(f"Reset rate limit for session {session_id} in operation {operation_name}")
            else:
                # Reset session across all operations
                for op_name in list(self._sessions.keys()):
                    if session_id in self._sessions[op_name]:
                        del self._sessions[op_name][session_id]
                        if not self._sessions[op_name]:
                            del self._sessions[op_name]

                logger.info(f"Reset rate limit for session {session_id} across all operations")

    def clear_all_sessions(self):
        """Clear all rate limit sessions (useful for testing)."""
        with self._lock:
            session_count = sum(len(sessions) for sessions in self._sessions.values())
            self._sessions.clear()
            logger.info(f"Cleared all {session_count} rate limit sessions")


# Global rate limiter instance
_rate_limiter = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        with _limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()

    return _rate_limiter


def _extract_session_id() -> str:
    """
    Extract session ID from current context.

    Returns:
        Session identifier string
    """
    # Try to get session ID from Flask context
    try:
        from flask import session
        if session and 'session_id' in session:
            return session['session_id']
    except ImportError:
        pass

    # Try to get from request context
    try:
        from flask import request
        if request:
            # Use IP address as fallback
            ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            return hashlib.md5(f"{ip}:{datetime.now().date()}".encode()).hexdigest()[:16]
    except ImportError:
        pass

    # Fallback to thread-based session
    return f"thread_{threading.get_ident()}_{datetime.now().date()}"


def rate_limit(max_requests: int = None, window_seconds: int = None,
               operation_name: str = None, strategy: str = 'sliding_window'):
    """
    Rate limiting decorator with session-based tracking.

    Args:
        max_requests: Maximum requests allowed (uses rule default if None)
        window_seconds: Time window in seconds (uses rule default if None)
        operation_name: Operation name for rule lookup (defaults to function name)
        strategy: Rate limiting strategy (overrides rule default if specified)

    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determine operation name
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            # Get session ID
            session_id = _extract_session_id()

            # Get rate limiter
            limiter = get_rate_limiter()

            # Check rate limit
            result = limiter.check_rate_limit(session_id, op_name)

            if not result.allowed:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded for {op_name} "
                             f"session {session_id}: {result.current_usage}/{result.max_requests}")

                from flask import jsonify
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Maximum {result.max_requests} '
                              f'requests per {result.window_seconds} seconds allowed.',
                    'retry_after': result.retry_after,
                    'reset_time': result.reset_time.isoformat(),
                    'current_usage': result.current_usage,
                    'max_requests': result.max_requests
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(result.retry_after)
                response.headers['X-RateLimit-Limit'] = str(result.max_requests)
                response.headers['X-RateLimit-Remaining'] = str(result.remaining_requests)
                response.headers['X-RateLimit-Reset'] = str(int(result.reset_time.timestamp()))

                return response

            # Add rate limit headers to successful response
            # Note: This will only work if the function returns a Flask response
            # We'll handle this in a try/except block to avoid breaking non-Flask functions

            try:
                # Execute the function
                result_data = func(*args, **kwargs)

                # If it's a Flask response, add headers
                if hasattr(result_data, 'headers'):
                    result_data.headers['X-RateLimit-Limit'] = str(result.max_requests)
                    result_data.headers['X-RateLimit-Remaining'] = str(result.remaining_requests)
                    result_data.headers['X-RateLimit-Reset'] = str(int(result.reset_time.timestamp()))

                return result_data

            except Exception as e:
                # Log the exception and re-raise
                logger.error(f"Exception in rate-limited function {op_name}: {e}")
                raise

        return wrapper
    return decorator


def rate_limit_async(max_requests: int = None, window_seconds: int = None,
                     operation_name: str = None, strategy: str = 'sliding_window'):
    """
    Rate limiting decorator for async functions with session-based tracking.

    Args:
        max_requests: Maximum requests allowed (uses rule default if None)
        window_seconds: Time window in seconds (uses rule default if None)
        operation_name: Operation name for rule lookup (defaults to function name)
        strategy: Rate limiting strategy (overrides rule default if specified)

    Returns:
        Decorated async function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine operation name
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            # Get session ID
            session_id = _extract_session_id()

            # Get rate limiter
            limiter = get_rate_limiter()

            # Check rate limit
            result = limiter.check_rate_limit(session_id, op_name)

            if not result.allowed:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded for async {op_name} "
                             f"session {session_id}: {result.current_usage}/{result.max_requests}")

                # For async functions, we might be in a different context
                # Raise an exception that can be handled by the calling code
                from utils.error_handler import RateLimitError
                raise RateLimitError(
                    f"Rate limit exceeded: {result.current_usage}/{result.max_requests} "
                    f"requests per {result.window_seconds} seconds",
                    retry_after=result.retry_after,
                    reset_time=result.reset_time
                )

            # Execute the async function
            return await func(*args, **kwargs)

        return wrapper
    return decorator


# Convenience functions for common operations
def rate_limit_config_operation(operation_type: str):
    """
    Rate limiting for configuration operations with Security NFR enforcement.

    Args:
        operation_type: Type of configuration operation (load, save, validate, etc.)
    """
    return rate_limit(
        operation_name=f'config_{operation_type}',
        strategy='sliding_window'
    )


def rate_limit_api_operation(operation_type: str):
    """
    Rate limiting for API operations.

    Args:
        operation_type: Type of API operation (request, validation, etc.)
    """
    return rate_limit(
        operation_name=f'api_{operation_type}',
        strategy='sliding_window'
    )


def rate_limit_database_operation(operation_type: str):
    """
    Rate limiting for database operations.

    Args:
        operation_type: Type of database operation (query, write, etc.)
    """
    return rate_limit(
        operation_name=f'database_{operation_type}',
        strategy='sliding_window'
    )


def get_rate_limit_stats() -> Dict[str, Any]:
    """Get comprehensive rate limiting statistics."""
    return get_rate_limiter().get_statistics()


def reset_rate_limit_session(session_id: str, operation_name: str = None):
    """Reset rate limit for a specific session."""
    get_rate_limiter().reset_session(session_id, operation_name)


def clear_all_rate_limits():
    """Clear all rate limit sessions (useful for testing)."""
    get_rate_limiter().clear_all_sessions()


# Initialize rate limiting
logger.info("Rate limiting module initialized with session-based tracking")
logger.info("Security NFR: Configuration operations limited to 5 requests per minute")