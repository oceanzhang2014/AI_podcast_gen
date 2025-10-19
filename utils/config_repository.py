"""
Configuration Repository for Podcast Generation System

This module provides data access operations for user configurations with comprehensive
CRUD functionality, error handling, and performance optimization. It serves as the
data layer for configuration management, abstracting database operations and
providing a clean interface for configuration services.

Purpose: Provide core data access operations for user configurations with SQLite integration.
"""

import sqlite3
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pathlib import Path

from .database import get_database_manager, execute_query, execute_transaction
from .error_handler import (
    DatabaseError, ValidationError, handle_errors, get_logger
)
from config import (
    UserConfig, APIKeyConfig, AgentModelConfig,
    SUPPORTED_AI_PROVIDERS, validate_provider_name
)


class ConfigRepository:
    """
    Repository class for managing user configuration data in SQLite database.

    This class provides comprehensive CRUD operations for user configurations,
    API keys, and agent settings with proper error handling, parameter validation,
    and performance optimization through the existing database infrastructure.
    """

    def __init__(self, db_manager=None):
        """
        Initialize the configuration repository.

        Args:
            db_manager: Optional database manager instance. If None, uses global instance.
        """
        self.db_manager = db_manager or get_database_manager()
        self.logger = get_logger()
        self.logger.debug("ConfigRepository initialized")

    @handle_errors("create user configuration", reraise=True)
    def create_user_config(self, session_id: str) -> UserConfig:
        """
        Create a new user configuration entry in the database.

        Args:
            session_id: Unique session identifier for the user

        Returns:
            UserConfig: Newly created user configuration

        Raises:
            ValidationError: If session_id is invalid
            DatabaseError: If database operation fails
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        if len(session_id.strip()) == 0:
            raise ValidationError("Session ID cannot be empty or whitespace", field="session_id")

        session_id = session_id.strip()

        # Check if user already exists
        existing_config = self.get_user_config(session_id)
        if existing_config:
            self.logger.warning(f"User configuration already exists for session: {session_id}")
            return existing_config

        try:
            with self.db_manager.get_connection() as conn:
                # Create user record
                cursor = conn.execute(
                    "INSERT INTO users (session_id) VALUES (?)",
                    (session_id,)
                )
                user_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Created new user configuration for session: {session_id} (ID: {user_id})")

                # Log the configuration creation
                self.log_configuration_change(
                    session_id=session_id,
                    action="create_user",
                    details=f"Created new user configuration for session: {session_id}"
                )

                # Return empty configuration
                return UserConfig(
                    session_id=session_id,
                    api_keys=[],
                    agent_configs=[],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                # Session already exists, fetch existing config
                return self.get_user_config(session_id)
            raise DatabaseError(f"Failed to create user configuration: {str(e)}", original_error=e)
        except sqlite3.Error as e:
            raise DatabaseError(f"Database error creating user configuration: {str(e)}", original_error=e)

    @handle_errors("get user configuration", reraise=True)
    def get_user_config(self, session_id: str) -> Optional[UserConfig]:
        """
        Retrieve user configuration from the database.

        Args:
            session_id: Session identifier to retrieve configuration for

        Returns:
            Optional[UserConfig]: User configuration if found, None otherwise

        Raises:
            ValidationError: If session_id is invalid
            DatabaseError: If database operation fails
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        session_id = session_id.strip()

        try:
            with self.db_manager.get_connection() as conn:
                # Get user information
                user_result = conn.execute(
                    "SELECT id, session_id, created_at, updated_at FROM users WHERE session_id = ?",
                    (session_id,)
                ).fetchone()

                if not user_result:
                    self.logger.debug(f"No user configuration found for session: {session_id}")
                    return None

                user_id = user_result['id']
                self.logger.debug(f"Found user configuration for session: {session_id} (ID: {user_id})")

                # Get API keys for this user
                api_keys_result = conn.execute(
                    """
                    SELECT provider, encrypted_key, key_mask, is_valid, created_at, updated_at
                    FROM api_keys WHERE user_id = ? ORDER BY created_at
                    """,
                    (user_id,)
                ).fetchall()

                api_keys = []
                for api_key_row in api_keys_result:
                    api_keys.append(APIKeyConfig(
                        provider=api_key_row['provider'],
                        encrypted_key=api_key_row['encrypted_key'],
                        key_mask=api_key_row['key_mask'],
                        is_valid=bool(api_key_row['is_valid']),
                        created_at=datetime.fromisoformat(api_key_row['created_at']),
                        updated_at=datetime.fromisoformat(api_key_row['updated_at'])
                    ))

                # Get agent configurations for this user
                agent_configs_result = conn.execute(
                    """
                    SELECT agent_id, provider, model, created_at, updated_at
                    FROM agent_configs WHERE user_id = ? ORDER BY created_at
                    """,
                    (user_id,)
                ).fetchall()

                agent_configs = []
                for agent_config_row in agent_configs_result:
                    agent_configs.append(AgentModelConfig(
                        agent_id=agent_config_row['agent_id'],
                        provider=agent_config_row['provider'],
                        model=agent_config_row['model'],
                        created_at=datetime.fromisoformat(agent_config_row['created_at']),
                        updated_at=datetime.fromisoformat(agent_config_row['updated_at'])
                    ))

                # Construct and return UserConfig
                return UserConfig(
                    session_id=user_result['session_id'],
                    api_keys=api_keys,
                    agent_configs=agent_configs,
                    created_at=datetime.fromisoformat(user_result['created_at']),
                    updated_at=datetime.fromisoformat(user_result['updated_at'])
                )

        except sqlite3.Error as e:
            raise DatabaseError(f"Database error retrieving user configuration: {str(e)}", original_error=e)

    @handle_errors("update user configuration", reraise=True)
    def update_user_config(self, session_id: str, config: UserConfig) -> bool:
        """
        Update user configuration in the database.

        Args:
            session_id: Session identifier for the user
            config: Updated user configuration

        Returns:
            bool: True if update successful, False otherwise

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If database operation fails
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        if not isinstance(config, UserConfig):
            raise ValidationError("Config must be a UserConfig instance", field="config")

        if config.session_id != session_id:
            raise ValidationError("Config session ID must match provided session ID", field="session_id")

        session_id = session_id.strip()

        # Check if user exists
        existing_user = execute_query(
            "SELECT id FROM users WHERE session_id = ?",
            (session_id,),
            fetch_one=True
        )

        if not existing_user:
            self.logger.warning(f"Attempted to update non-existent user configuration: {session_id}")
            return False

        user_id = existing_user['id']

        try:
            # Use transaction for atomic updates
            queries = []

            # Clear existing API keys for this user
            queries.append(("DELETE FROM api_keys WHERE user_id = ?", (user_id,)))

            # Insert new API keys
            for api_key in config.api_keys:
                if not isinstance(api_key, APIKeyConfig):
                    raise ValidationError("All API keys must be APIKeyConfig instances", field="api_keys")

                # Validate provider
                if not validate_provider_name(api_key.provider):
                    raise ValidationError(f"Unsupported provider: {api_key.provider}", field="provider")

                queries.append((
                    """
                    INSERT INTO api_keys (user_id, provider, encrypted_key, key_mask, is_valid, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        api_key.provider,
                        api_key.encrypted_key,
                        api_key.key_mask,
                        api_key.is_valid,
                        api_key.created_at.isoformat(),
                        api_key.updated_at.isoformat()
                    )
                ))

            # Clear existing agent configurations for this user
            queries.append(("DELETE FROM agent_configs WHERE user_id = ?", (user_id,)))

            # Insert new agent configurations
            for agent_config in config.agent_configs:
                if not isinstance(agent_config, AgentModelConfig):
                    raise ValidationError("All agent configs must be AgentModelConfig instances", field="agent_configs")

                # Validate provider
                if not validate_provider_name(agent_config.provider):
                    raise ValidationError(f"Unsupported provider: {agent_config.provider}", field="provider")

                queries.append((
                    """
                    INSERT INTO agent_configs (user_id, agent_id, provider, model, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        agent_config.agent_id,
                        agent_config.provider,
                        agent_config.model,
                        agent_config.created_at.isoformat(),
                        agent_config.updated_at.isoformat()
                    )
                ))

            # Execute all queries in a transaction
            execute_transaction(queries)

            # Log the configuration update
            self.log_configuration_change(
                session_id=session_id,
                action="update_config",
                details=f"Updated {len(config.api_keys)} API keys and {len(config.agent_configs)} agent configurations"
            )

            self.logger.info(f"Updated user configuration for session: {session_id}")
            return True

        except Exception as e:
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Failed to update user configuration: {str(e)}", original_error=e)

    @handle_errors("delete user configuration", reraise=True)
    def delete_user_config(self, session_id: str) -> bool:
        """
        Delete user configuration from the database.

        Args:
            session_id: Session identifier for the user to delete

        Returns:
            bool: True if deletion successful, False otherwise

        Raises:
            ValidationError: If session_id is invalid
            DatabaseError: If database operation fails
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        session_id = session_id.strip()

        try:
            with self.db_manager.get_connection() as conn:
                # Check if user exists
                user_result = conn.execute(
                    "SELECT id FROM users WHERE session_id = ?",
                    (session_id,)
                ).fetchone()

                if not user_result:
                    self.logger.debug(f"No user configuration found to delete for session: {session_id}")
                    return False

                user_id = user_result['id']

                # Delete user (cascade delete will handle related records)
                cursor = conn.execute(
                    "DELETE FROM users WHERE id = ?",
                    (user_id,)
                )
                conn.commit()

                # Delete user (cascade delete will handle related records)
                cursor = conn.execute(
                    "DELETE FROM users WHERE id = ?",
                    (user_id,)
                )
                conn.commit()

                deleted_count = cursor.rowcount
                success = deleted_count > 0

                if success:
                    self.logger.info(f"Deleted user configuration for session: {session_id}")
                else:
                    self.logger.warning(f"Failed to delete user configuration for session: {session_id}")

                return success

        except sqlite3.Error as e:
            raise DatabaseError(f"Database error deleting user configuration: {str(e)}", original_error=e)

    @handle_errors("log configuration change", reraise=False)
    def log_configuration_change(self, session_id: str, action: str, details: str = None) -> bool:
        """
        Log a configuration change for audit purposes.

        This method provides comprehensive audit logging for all configuration modifications,
        including user creation, updates, deletions, API key changes, and agent configuration
        modifications. The audit log supports security monitoring, debugging, and compliance
        requirements as specified in the Reliability NFRs.

        Args:
            session_id: Session identifier for the user
            action: Action being performed (e.g., 'create_user', 'update_config', 'delete_user',
                   'add_api_key', 'remove_api_key', 'update_agent_config')
            details: Optional additional details about the change (e.g., specific fields modified,
                    providers involved, counts of changes)

        Returns:
            bool: True if logging successful, False otherwise

        Examples:
            >>> log_configuration_change("session123", "add_api_key", "Added DeepSeek API key")
            >>> log_configuration_change("session123", "update_config", "Updated 2 API keys and 3 agent configs")
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            self.logger.warning("Invalid session_id provided for audit logging")
            return False

        if not action or not isinstance(action, str):
            self.logger.warning("Invalid action provided for audit logging")
            return False

        session_id = session_id.strip()
        action = action.strip()

        # Validate action against known audit actions
        valid_actions = {
            'create_user', 'update_config', 'delete_user',
            'add_api_key', 'remove_api_key', 'update_api_key',
            'add_agent_config', 'remove_agent_config', 'update_agent_config',
            'clear_all_config', 'export_config', 'import_config',
            'validate_api_key', 'login', 'logout'
        }

        if action not in valid_actions:
            self.logger.warning(f"Unknown audit action: {action}. Logging anyway for security monitoring.")

        # Limit details length to prevent database bloat
        if details and len(details) > 1000:
            details = details[:1000] + "... (truncated)"

        try:
            # Get user ID
            user_result = execute_query(
                "SELECT id FROM users WHERE session_id = ?",
                (session_id,),
                fetch_one=True
            )

            if not user_result:
                self.logger.warning(f"Cannot log change for non-existent session: {session_id}")
                return False

            user_id = user_result['id']

            # Insert audit log entry
            execute_query(
                "INSERT INTO config_audit_log (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details),
                fetch_all=False
            )

            self.logger.debug(f"Logged configuration change: {action} for session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to log configuration change: {str(e)}")
            return False

    @handle_errors("get available models", reraise=True)
    def get_available_models(self, session_id: str) -> Dict[str, List[str]]:
        """
        Get available models for each configured API provider.

        Args:
            session_id: Session identifier for the user

        Returns:
            Dict[str, List[str]]: Dictionary mapping providers to their available models

        Raises:
            ValidationError: If session_id is invalid
            DatabaseError: If database operation fails
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        session_id = session_id.strip()

        # Get user configuration
        user_config = self.get_user_config(session_id)
        if not user_config:
            return {}

        # Build available models dictionary
        available_models = {}
        for api_key in user_config.api_keys:
            if api_key.is_valid and api_key.provider in SUPPORTED_AI_PROVIDERS:
                provider_info = SUPPORTED_AI_PROVIDERS[api_key.provider]
                available_models[api_key.provider] = provider_info['models'].copy()

        return available_models

    @handle_errors("backup database", reraise=False)
    def backup_database(self, backup_path: Union[str, Path] = None) -> bool:
        """
        Create a backup of the configuration database.

        Args:
            backup_path: Optional custom backup path. If None, creates timestamped backup.

        Returns:
            bool: True if backup successful, False otherwise
        """
        try:
            if backup_path:
                backup_path = Path(backup_path)

            success = self.db_manager.backup_database(backup_path)

            if success:
                self.logger.info(f"Database backup created successfully: {backup_path or 'auto-generated'}")
            else:
                self.logger.error("Database backup failed")

            return success

        except Exception as e:
            self.logger.error(f"Database backup failed with error: {str(e)}")
            return False

    @handle_errors("get audit log", reraise=True)
    def get_audit_log(self, session_id: str = None, limit: int = 100,
                      start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit log entries for configuration changes.

        Args:
            session_id: Optional session identifier to filter by user. If None, returns all entries.
            limit: Maximum number of entries to return (default: 100)
            start_date: Optional start date to filter entries
            end_date: Optional end date to filter entries

        Returns:
            List[Dict[str, Any]]: List of audit log entries with session_id, action, details, and timestamp

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If database operation fails
        """
        # Validate input parameters
        if session_id is not None:
            if not session_id or not isinstance(session_id, str):
                raise ValidationError("Session ID must be a non-empty string or None", field="session_id")
            session_id = session_id.strip()

        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError("Limit must be a positive integer", field="limit")

        if limit > 1000:
            raise ValidationError("Limit cannot exceed 1000 entries", field="limit")

        try:
            with self.db_manager.get_connection() as conn:
                # Build base query with session_id filter if provided
                if session_id:
                    # First get user_id from session_id
                    user_result = conn.execute(
                        "SELECT id FROM users WHERE session_id = ?",
                        (session_id,)
                    ).fetchone()

                    if not user_result:
                        self.logger.debug(f"No user found for session: {session_id}")
                        return []

                    user_id = user_result['id']
                    base_query = "SELECT u.session_id, cal.action, cal.details, cal.timestamp "
                    base_query += "FROM config_audit_log cal JOIN users u ON cal.user_id = u.id "
                    base_query += "WHERE cal.user_id = ? "
                    base_params = [user_id]
                else:
                    base_query = "SELECT u.session_id, cal.action, cal.details, cal.timestamp "
                    base_query += "FROM config_audit_log cal JOIN users u ON cal.user_id = u.id "
                    base_params = []

                # Add date filters if provided
                if start_date:
                    base_query += "AND cal.timestamp >= ? "
                    base_params.append(start_date.isoformat())

                if end_date:
                    base_query += "AND cal.timestamp <= ? "
                    base_params.append(end_date.isoformat())

                # Add ordering and limit
                base_query += "ORDER BY cal.timestamp DESC LIMIT ?"
                base_params.append(limit)

                # Execute query
                audit_entries = conn.execute(base_query, tuple(base_params)).fetchall()

                # Format results
                audit_log = []
                for entry in audit_entries:
                    audit_log.append({
                        'session_id': entry['session_id'],
                        'action': entry['action'],
                        'details': entry['details'],
                        'timestamp': entry['timestamp']
                    })

                self.logger.debug(f"Retrieved {len(audit_log)} audit log entries")
                return audit_log

        except sqlite3.Error as e:
            raise DatabaseError(f"Database error retrieving audit log: {str(e)}", original_error=e)

    @handle_errors("get configuration statistics", reraise=False)
    def get_configuration_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored configurations.

        Returns:
            Dict[str, Any]: Configuration statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Get user count
                user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']

                # Get API key count by provider
                api_key_stats = conn.execute("""
                    SELECT provider, COUNT(*) as count, SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) as valid_count
                    FROM api_keys GROUP BY provider
                """).fetchall()

                # Get agent configuration count
                agent_config_count = conn.execute("SELECT COUNT(*) as count FROM agent_configs").fetchone()['count']

                # Get recent activity
                recent_activity = conn.execute("""
                    SELECT u.session_id, cal.action, cal.timestamp
                    FROM config_audit_log cal
                    JOIN users u ON cal.user_id = u.id
                    ORDER BY cal.timestamp DESC LIMIT 10
                """).fetchall()

                statistics = {
                    'total_users': user_count,
                    'total_agent_configs': agent_config_count,
                    'api_keys_by_provider': [
                        {
                            'provider': stat['provider'],
                            'total_count': stat['count'],
                            'valid_count': stat['valid_count']
                        }
                        for stat in api_key_stats
                    ],
                    'recent_activity': [
                        {
                            'session_id': activity['session_id'],
                            'action': activity['action'],
                            'timestamp': activity['timestamp']
                        }
                        for activity in recent_activity
                    ],
                    'generated_at': datetime.now().isoformat()
                }

                self.logger.debug("Configuration statistics retrieved successfully")
                return statistics

        except Exception as e:
            self.logger.error(f"Failed to retrieve configuration statistics: {str(e)}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

    def close(self):
        """Close database connections and cleanup resources."""
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close_thread_connection()
            self.logger.debug("ConfigRepository database connections closed")


# Global repository instance for convenience
_config_repository = None


def get_config_repository() -> ConfigRepository:
    """
    Get the global configuration repository instance.

    Returns:
        ConfigRepository: Global repository instance
    """
    global _config_repository
    if _config_repository is None:
        _config_repository = ConfigRepository()
    return _config_repository


# Convenience functions for common operations
def create_user_config(session_id: str) -> UserConfig:
    """Create a new user configuration using the global repository."""
    repository = get_config_repository()
    return repository.create_user_config(session_id)


def get_user_config(session_id: str) -> Optional[UserConfig]:
    """Get user configuration using the global repository."""
    repository = get_config_repository()
    return repository.get_user_config(session_id)


def update_user_config(session_id: str, config: UserConfig) -> bool:
    """Update user configuration using the global repository."""
    repository = get_config_repository()
    return repository.update_user_config(session_id, config)


def delete_user_config(session_id: str) -> bool:
    """Delete user configuration using the global repository."""
    repository = get_config_repository()
    return repository.delete_user_config(session_id)


def log_configuration_change(session_id: str, action: str, details: str = None) -> bool:
    """Log configuration change using the global repository."""
    repository = get_config_repository()
    return repository.log_configuration_change(session_id, action, details)


def get_available_models(session_id: str) -> Dict[str, List[str]]:
    """Get available models using the global repository."""
    repository = get_config_repository()
    return repository.get_available_models(session_id)


def get_audit_log(session_id: str = None, limit: int = 100,
                 start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
    """Get audit log entries using the global repository."""
    repository = get_config_repository()
    return repository.get_audit_log(session_id, limit, start_date, end_date)


# Module initialization
def _initialize_module():
    """Initialize the configuration repository module."""
    try:
        logger = get_logger()
        logger.info("Initializing configuration repository module")

        # Create global repository instance
        repository = get_config_repository()

        # Log initialization success
        logger.info("Configuration repository module initialized successfully")

    except Exception as e:
        logger = get_logger()
        logger.error(f"Configuration repository module initialization failed: {str(e)}")
        raise


# Initialize module on import
_initialize_module()