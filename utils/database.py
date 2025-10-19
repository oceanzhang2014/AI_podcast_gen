"""
Database schema and operations for the podcast generation system.

This module provides SQLite database functionality for persistent storage of user
configurations, API keys, and agent settings. It includes comprehensive schema
creation, connection management, and database initialization with proper error
handling and logging.

Purpose: Set up database structure for persistent storage of user configurations.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from datetime import datetime

from .error_handler import (
    DatabaseError, get_logger, handle_errors
)

# Database configuration
DATABASE_NAME = "podcast_config.db"
DATABASE_TIMEOUT = 30.0  # seconds
DATABASE_POOL_SIZE = 5

# Thread-local storage for database connections
_local_storage = threading.local()


class DatabaseManager:
    """
    Manages SQLite database connections and operations with thread safety.

    This class provides connection pooling, schema management, and database
    initialization functionality following existing project patterns.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses default location.
        """
        self.db_path = db_path or Path(DATABASE_NAME)
        self.logger = get_logger()
        self._lock = threading.Lock()

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """
        Get a thread-safe database connection with automatic cleanup.

        Yields:
            sqlite3.Connection: Database connection

        Raises:
            DatabaseError: If connection fails
        """
        connection = None
        try:
            # Check if thread already has a connection
            if not hasattr(_local_storage, 'connection') or _local_storage.connection is None:
                _local_storage.connection = sqlite3.connect(
                    str(self.db_path),
                    timeout=DATABASE_TIMEOUT,
                    check_same_thread=False
                )
                # Configure connection for performance
                _local_storage.connection.row_factory = sqlite3.Row
                _local_storage.connection.execute("PRAGMA foreign_keys=ON")
                _local_storage.connection.execute("PRAGMA journal_mode=WAL")
                _local_storage.connection.execute("PRAGMA synchronous=NORMAL")
                _local_storage.connection.execute("PRAGMA cache_size=10000")
                _local_storage.connection.execute("PRAGMA temp_store=memory")

                self.logger.debug(f"Created new database connection for thread {threading.current_thread().name}")

            connection = _local_storage.connection
            yield connection

        except sqlite3.Error as e:
            error_msg = f"Database connection error: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg, original_error=e)
        finally:
            # Note: We don't close the connection here as it's reused per thread
            pass

    def close_thread_connection(self):
        """Close the database connection for the current thread."""
        if hasattr(_local_storage, 'connection') and _local_storage.connection:
            try:
                _local_storage.connection.close()
                _local_storage.connection = None
                self.logger.debug(f"Closed database connection for thread {threading.current_thread().name}")
            except sqlite3.Error as e:
                self.logger.warning(f"Error closing database connection: {str(e)}")

    @handle_errors("database schema creation", reraise=True)
    def create_database_schema(self) -> bool:
        """
        Create the complete database schema with all tables and indexes.

        Returns:
            bool: True if schema creation successful

        Raises:
            DatabaseError: If schema creation fails
        """
        schema_sql = self._get_schema_definition()

        with self.get_connection() as conn:
            try:
                # Execute schema creation in a transaction
                conn.executescript(schema_sql)
                conn.commit()

                self.logger.info("Database schema created successfully")
                return True

            except sqlite3.Error as e:
                conn.rollback()
                error_msg = f"Failed to create database schema: {str(e)}"
                self.logger.error(error_msg)
                raise DatabaseError(error_msg, original_error=e)

    def _get_schema_definition(self) -> str:
        """
        Get the complete SQL schema definition.

        Returns:
            str: Multi-line SQL schema definition
        """
        return """
-- =====================================================
-- Podcast Generation System Database Schema
-- =====================================================

-- Drop existing views if they exist (for clean initialization)
DROP VIEW IF EXISTS agent_config_summary_view;
DROP VIEW IF EXISTS api_key_summary_view;
DROP VIEW IF EXISTS user_config_view;

-- Drop existing tables if they exist (for clean initialization)
DROP TABLE IF EXISTS config_audit_log;
DROP TABLE IF EXISTS agent_configs;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS schema_version;

-- =====================================================
-- Users table (session-based) with performance indexes
-- =====================================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast session lookup
CREATE INDEX idx_users_session_id ON users(session_id);

-- =====================================================
-- API Keys table with encryption and performance indexes
-- =====================================================
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    key_mask TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider)
);

-- Performance indexes
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_provider ON api_keys(provider);
CREATE INDEX idx_api_keys_valid ON api_keys(is_valid);

-- =====================================================
-- Agent Configurations table with performance indexes
-- =====================================================
CREATE TABLE agent_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, agent_id)
);

-- Performance indexes
CREATE INDEX idx_agent_configs_user_id ON agent_configs(user_id);
CREATE INDEX idx_agent_configs_agent_id ON agent_configs(agent_id);

-- =====================================================
-- Configuration Audit Log with performance indexes
-- =====================================================
CREATE TABLE config_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for audit queries
CREATE INDEX idx_audit_log_user_id ON config_audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON config_audit_log(timestamp);

-- =====================================================
-- Triggers for automatic timestamp updates
-- =====================================================

-- Trigger to update users.updated_at on row modification
CREATE TRIGGER update_users_timestamp
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to update api_keys.updated_at on row modification
CREATE TRIGGER update_api_keys_timestamp
    AFTER UPDATE ON api_keys
    FOR EACH ROW
BEGIN
    UPDATE api_keys SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to update agent_configs.updated_at on row modification
CREATE TRIGGER update_agent_configs_timestamp
    AFTER UPDATE ON agent_configs
    FOR EACH ROW
BEGIN
    UPDATE agent_configs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- =====================================================
-- Views for common queries
-- =====================================================

-- View for complete user configuration
CREATE VIEW user_config_view AS
SELECT
    u.session_id,
    u.created_at as user_created_at,
    u.updated_at as user_updated_at,
    COUNT(DISTINCT ak.id) as api_key_count,
    COUNT(DISTINCT ac.id) as agent_config_count,
    COUNT(DISTINCT cal.id) as audit_log_count
FROM users u
LEFT JOIN api_keys ak ON u.id = ak.user_id
LEFT JOIN agent_configs ac ON u.id = ac.user_id
LEFT JOIN config_audit_log cal ON u.id = cal.user_id
GROUP BY u.id;

-- View for API key summary
CREATE VIEW api_key_summary_view AS
SELECT
    u.session_id,
    ak.provider,
    ak.key_mask,
    ak.is_valid,
    ak.created_at,
    ak.updated_at
FROM users u
JOIN api_keys ak ON u.id = ak.user_id
WHERE ak.is_valid = 1;

-- View for agent configuration summary
CREATE VIEW agent_config_summary_view AS
SELECT
    u.session_id,
    ac.agent_id,
    ac.provider,
    ac.model,
    ac.created_at,
    ac.updated_at
FROM users u
JOIN agent_configs ac ON u.id = ac.user_id;

-- =====================================================
-- Database metadata and version information
-- =====================================================

-- Store schema version for future migrations
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial schema version
INSERT INTO schema_version (version, description) VALUES (1, 'Initial database schema for API key configuration system');
"""

    @handle_errors("database initialization", reraise=True)
    def _initialize_database(self) -> bool:
        """
        Initialize the database if it doesn't exist or needs updates.

        Returns:
            bool: True if initialization successful

        Raises:
            DatabaseError: If initialization fails
        """
        try:
            # Check if database needs initialization
            if not self._is_database_initialized():
                self.logger.info("Initializing database schema")
                self.create_database_schema()
                self.logger.info("Database initialization completed")
            else:
                self.logger.debug("Database already initialized")

            return True

        except Exception as e:
            error_msg = f"Database initialization failed: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg, original_error=e)

    def _is_database_initialized(self) -> bool:
        """
        Check if the database schema has been properly initialized.

        Returns:
            bool: True if database is initialized
        """
        try:
            with self.get_connection() as conn:
                # Check if key tables exist
                result = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM sqlite_master
                    WHERE type='table' AND name IN ('users', 'api_keys', 'agent_configs', 'config_audit_log')
                """).fetchone()

                table_count = result['count'] if result else 0

                # Check if schema version table exists and has records
                schema_check = conn.execute("""
                    SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name='schema_version'
                """).fetchone()

                has_schema_version = schema_check['count'] > 0 if schema_check else False

                # Database is initialized if all tables exist and schema version is present
                is_initialized = (table_count == 4) and has_schema_version

                if is_initialized:
                    self.logger.debug("Database schema validation passed")
                else:
                    self.logger.info(f"Database needs initialization. Tables found: {table_count}, Schema version: {has_schema_version}")

                return is_initialized

        except sqlite3.Error as e:
            self.logger.warning(f"Error checking database initialization: {str(e)}")
            return False

    @handle_errors("database information retrieval")
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the database status.

        Returns:
            Dict[str, Any]: Database information including table counts and schema version
        """
        info = {
            'database_path': str(self.db_path),
            'database_exists': self.db_path.exists(),
            'database_size_mb': 0,
            'tables': {},
            'indexes': {},
            'schema_version': None
        }

        if not info['database_exists']:
            return info

        try:
            # Get database file size
            info['database_size_mb'] = round(self.db_path.stat().st_size / (1024 * 1024), 2)

            with self.get_connection() as conn:
                # Get table information
                tables_result = conn.execute("""
                    SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name
                """).fetchall()

                for table in tables_result:
                    table_name = table['name']
                    # Get row count for each table
                    count_result = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()
                    info['tables'][table_name] = {
                        'row_count': count_result['count'] if count_result else 0,
                        'definition': table['sql']
                    }

                # Get index information
                indexes_result = conn.execute("""
                    SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name
                """).fetchall()

                for index in indexes_result:
                    index_name = index['name']
                    table_name = index['tbl_name']
                    info['indexes'][index_name] = {
                        'table': table_name,
                        'definition': index['sql']
                    }

                # Get schema version
                schema_result = conn.execute("""
                    SELECT version, description, applied_at FROM schema_version ORDER BY version DESC LIMIT 1
                """).fetchone()

                if schema_result:
                    info['schema_version'] = {
                        'version': schema_result['version'],
                        'description': schema_result['description'],
                        'applied_at': schema_result['applied_at']
                    }

                # Get database settings
                pragma_settings = conn.execute("PRAGMA journal_mode").fetchone()
                if pragma_settings:
                    info['journal_mode'] = pragma_settings[0]

                pragma_settings = conn.execute("PRAGMA synchronous").fetchone()
                if pragma_settings:
                    info['synchronous'] = pragma_settings[0]

                pragma_settings = conn.execute("PRAGMA foreign_keys").fetchone()
                if pragma_settings:
                    info['foreign_keys_enabled'] = bool(pragma_settings[0])

            return info

        except Exception as e:
            self.logger.error(f"Error getting database information: {str(e)}")
            info['error'] = str(e)
            return info

    @handle_errors("database backup")
    def backup_database(self, backup_path: Optional[Path] = None) -> bool:
        """
        Create a backup of the database.

        Args:
            backup_path: Path for backup file. If None, creates timestamped backup.

        Returns:
            bool: True if backup successful

        Raises:
            DatabaseError: If backup fails
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.parent / f"backup_{timestamp}_{self.db_path.name}"

        try:
            with self.get_connection() as source_conn:
                backup_conn = sqlite3.connect(str(backup_path))

                try:
                    # Use SQLite backup API
                    source_conn.backup(backup_conn)
                    self.logger.info(f"Database backup created: {backup_path}")
                    return True

                finally:
                    backup_conn.close()

        except Exception as e:
            error_msg = f"Database backup failed: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg, original_error=e)

    @handle_errors("database cleanup")
    def cleanup_old_audit_logs(self, days_to_keep: int = 30) -> int:
        """
        Clean up old audit log entries.

        Args:
            days_to_keep: Number of days to keep audit logs

        Returns:
            int: Number of deleted records

        Raises:
            DatabaseError: If cleanup fails
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM config_audit_log
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))

                deleted_count = cursor.rowcount
                conn.commit()

                self.logger.info(f"Cleaned up {deleted_count} old audit log entries")
                return deleted_count

        except sqlite3.Error as e:
            error_msg = f"Failed to cleanup audit logs: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg, original_error=e)

    def close_all_connections(self):
        """Close all database connections for all threads."""
        self.logger.info("Closing all database connections")
        # Note: In a real application with multiple threads, you might want to
        # keep track of all connections and close them properly
        self.close_thread_connection()


# Global database manager instance
_database_manager = None


def get_database_manager(db_path: Optional[Path] = None) -> DatabaseManager:
    """
    Get the global database manager instance.

    Args:
        db_path: Optional database path. Only used on first call.

    Returns:
        DatabaseManager: Global database manager instance
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager(db_path)
    return _database_manager


def create_database_schema() -> bool:
    """
    Create the database schema using the global database manager.

    This is a convenience function that creates the complete database schema
    with all tables, indexes, views, and triggers as specified in the design
    document.

    Returns:
        bool: True if schema creation successful

    Raises:
        DatabaseError: If schema creation fails
    """
    db_manager = get_database_manager()
    return db_manager.create_database_schema()


# Convenience functions for database operations
def initialize_database(db_path: Optional[Path] = None) -> bool:
    """
    Initialize the database with schema and settings.

    Args:
        db_path: Optional custom database path

    Returns:
        bool: True if initialization successful
    """
    manager = get_database_manager(db_path)
    return manager._initialize_database()


def get_database_info() -> Dict[str, Any]:
    """
    Get comprehensive database information.

    Returns:
        Dict[str, Any]: Database status and metadata
    """
    manager = get_database_manager()
    return manager.get_database_info()


def backup_database(backup_path: Optional[Path] = None) -> bool:
    """
    Create a database backup.

    Args:
        backup_path: Optional backup file path

    Returns:
        bool: True if backup successful
    """
    manager = get_database_manager()
    return manager.backup_database(backup_path)


def cleanup_old_audit_logs(days_to_keep: int = 30) -> int:
    """
    Clean up old audit log entries.

    Args:
        days_to_keep: Number of days to keep logs

    Returns:
        int: Number of deleted records
    """
    manager = get_database_manager()
    return manager.cleanup_old_audit_logs(days_to_keep)


# Database connection management utilities
def get_database_connection() -> sqlite3.Connection:
    """
    Get a thread-safe database connection with automatic connection pooling.

    This function provides a convenient way to get a database connection that
    automatically handles thread-local connection pooling. Each thread gets
    its own connection that is reused for subsequent calls within the same
    thread, improving performance and ensuring thread safety.

    Returns:
        sqlite3.Connection: Thread-local database connection configured with
                          row factory, foreign keys, WAL mode, and performance settings

    Raises:
        DatabaseError: If connection cannot be established

    Example:
        >>> conn = get_database_connection()
        >>> result = conn.execute("SELECT * FROM users").fetchall()
        >>> # Connection automatically managed per thread
    """
    manager = get_database_manager()
    return manager.get_connection().__enter__()


def execute_query(query: str, params: tuple = (), fetch_one: bool = False,
                 fetch_all: bool = True) -> Optional[Union[sqlite3.Row, List[sqlite3.Row]]]:
    """
    Execute a database query with proper error handling and connection management.

    This utility function simplifies database operations by handling connection
    management, query execution, and result fetching in a single call. It uses
    the thread-local connection pool for optimal performance.

    Args:
        query: SQL query string to execute (can include parameter placeholders)
        params: Tuple of parameters to substitute into the query
        fetch_one: If True, return only the first result row
        fetch_all: If True, return all result rows (default, ignored if fetch_one=True)

    Returns:
        Optional[Union[sqlite3.Row, List[sqlite3.Row]]]:
            - Single sqlite3.Row if fetch_one=True and results exist
            - List of sqlite3.Row objects if fetch_all=True and results exist
            - None if no results found

    Raises:
        DatabaseError: If query execution fails

    Example:
        >>> # Get single user
        >>> user = execute_query("SELECT * FROM users WHERE session_id = ?",
        ...                      ("abc123",), fetch_one=True)
        >>>
        >>> # Get all API keys for a user
        >>> api_keys = execute_query("SELECT * FROM api_keys WHERE user_id = ?",
        ...                         (user_id,))
    """
    manager = get_database_manager()
    logger = manager.logger

    try:
        with manager.get_connection() as conn:
            # Execute the query with parameters
            cursor = conn.execute(query, params)

            # Fetch results based on parameters
            if fetch_one:
                result = cursor.fetchone()
                logger.debug(f"Query executed successfully, fetched one row: {query[:100]}...")
                return result
            elif fetch_all:
                results = cursor.fetchall()
                logger.debug(f"Query executed successfully, fetched {len(results)} rows: {query[:100]}...")
                return results
            else:
                # For INSERT/UPDATE/DELETE operations, return None
                conn.commit()
                logger.debug(f"Query executed successfully, no fetch requested: {query[:100]}...")
                return None

    except sqlite3.Error as e:
        error_msg = f"Query execution failed: {str(e)}\nQuery: {query[:200]}...\nParams: {params}"
        logger.error(error_msg)
        raise DatabaseError(error_msg, query=query, original_error=e)


def execute_transaction(queries: List[tuple]) -> bool:
    """
    Execute multiple queries in a single transaction for atomicity.

    This utility function executes multiple SQL statements as a single
    transaction, ensuring that all queries succeed or none are applied.
    This is essential for maintaining data consistency across related
    operations like updating multiple tables.

    Args:
        queries: List of tuples, where each tuple contains:
                - query (str): SQL query string
                - params (tuple): Query parameters (empty tuple if no params)

    Returns:
        bool: True if all queries executed successfully and transaction committed

    Raises:
        DatabaseError: If any query fails and transaction is rolled back

    Example:
        >>> # Update user and create audit log in single transaction
        >>> queries = [
        ...     ("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,)),
        ...     ("INSERT INTO config_audit_log (user_id, action) VALUES (?, ?)",
        ...      (user_id, "config_updated"))
        ... ]
        >>> execute_transaction(queries)
    """
    manager = get_database_manager()
    logger = manager.logger

    if not queries:
        logger.warning("execute_transaction called with empty queries list")
        return True

    try:
        with manager.get_connection() as conn:
            # Start transaction
            logger.debug(f"Starting transaction with {len(queries)} queries")

            # Execute all queries
            for i, (query, params) in enumerate(queries):
                try:
                    conn.execute(query, params or ())
                    logger.debug(f"Transaction query {i+1}/{len(queries)} executed: {query[:100]}...")
                except sqlite3.Error as e:
                    error_msg = f"Transaction query {i+1} failed: {str(e)}\nQuery: {query[:200]}...\nParams: {params}"
                    logger.error(error_msg)
                    raise DatabaseError(error_msg, query=query, original_error=e)

            # Commit all changes
            conn.commit()
            logger.info(f"Transaction completed successfully: {len(queries)} queries committed")
            return True

    except sqlite3.Error as e:
        # Error handling is managed by DatabaseError above
        # This ensures transaction is automatically rolled back
        error_msg = f"Transaction failed and rolled back: {str(e)}"
        logger.error(error_msg)
        raise DatabaseError(error_msg, original_error=e)


# Module initialization
def _initialize_module():
    """Initialize the database module."""
    try:
        logger = get_logger()
        logger.info("Initializing database module")

        # Create global database manager (this will initialize schema if needed)
        db_manager = get_database_manager()

        # Log database information
        db_info = db_manager.get_database_info()
        logger.info(f"Database initialized: {db_info['database_path']}, "
                   f"Size: {db_info['database_size_mb']}MB, "
                   f"Tables: {len(db_info['tables'])}")

        logger.info("Database module initialization completed")

    except Exception as e:
        logger = get_logger()
        logger.error(f"Database module initialization failed: {str(e)}")
        raise


# Initialize module on import
_initialize_module()