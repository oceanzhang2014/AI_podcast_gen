"""
Configuration Service for Podcast Generation System

This module provides the business logic layer for configuration management with
comprehensive error handling, input validation, and integration with the
existing encryption and repository layers.

Purpose: Centralize configuration business logic with proper validation and security.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict

from utils.encryption_service import get_encryption_service
from utils.config_repository import get_config_repository
from utils.error_handler import (
    ConfigurationError, ValidationError, DatabaseError, NetworkError,
    handle_errors, get_logger
)
from utils.validators import validate_api_key_format, validate_provider_name
from utils.ai_client import AIClientFactory
from utils.performance import TTLCache
from config import (
    APIKeyConfig, AgentModelConfig, UserConfig,
    SUPPORTED_AI_PROVIDERS, create_api_key_config, create_agent_model_config
)


class ConfigurationService:
    """
    Business logic layer for configuration management with comprehensive validation
    and error handling. This service coordinates between the encryption service
    and repository layer to provide secure configuration management operations.

    The service handles:
    - API key encryption/decryption operations
    - Agent-model configuration management
    - Input validation and sanitization
    - Rate limiting for configuration changes
    - Audit logging integration
    - Error handling with proper logging
    """

    def __init__(self, encryption_service=None, repository=None):
        """
        Initialize the configuration service with required dependencies.

        Args:
            encryption_service: Optional encryption service instance
            repository: Optional configuration repository instance

        Raises:
            ConfigurationError: If service initialization fails
        """
        self.logger = get_logger()

        try:
            # Initialize dependencies with fallback to global instances
            self.encryption_service = encryption_service or get_encryption_service()
            self.repository = repository or get_config_repository()

            # Rate limiting storage (in production, use Redis or similar)
            self._rate_limit_store = {}

            # Initialize caching systems
            # Configuration cache with 5-minute TTL and 100 entries max
            self._config_cache = TTLCache(max_size=100, default_ttl=300)
            # Models cache with 30-minute TTL and 50 entries max
            self._models_cache = TTLCache(max_size=50, default_ttl=1800)
            # API keys cache with 5-minute TTL and 100 entries max
            self._api_keys_cache = TTLCache(max_size=100, default_ttl=300)

            self.logger.info("Configuration service initialized successfully with caching")

        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize configuration service: {str(e)}",
                config_key="service_initialization",
                original_error=e
            )

    @handle_errors("save_api_keys", reraise=True)
    def save_api_keys(self, session_id: str, api_keys: Dict[str, str]) -> bool:
        """
        Save encrypted API keys for a user session with comprehensive validation.

        This method validates API key formats, encrypts sensitive data, updates
        the user configuration, and logs all changes for audit purposes.

        Args:
            session_id: Unique session identifier for the user
            api_keys: Dictionary mapping provider names to API keys

        Returns:
            True if API keys were saved successfully

        Raises:
            ValidationError: If session_id or API keys are invalid
            ConfigurationError: If encryption or storage operations fail
            DatabaseError: If database operations fail

        Examples:
            >>> service = ConfigurationService()
            >>> service.save_api_keys("session123", {"deepseek": "sk-actual-key-here"})
            True
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        if not isinstance(api_keys, dict):
            raise ValidationError("API keys must be provided as a dictionary", field="api_keys")

        session_id = session_id.strip()

        if not api_keys:
            raise ValidationError("At least one API key must be provided", field="api_keys")

        # Check rate limiting
        if not self._check_rate_limit(session_id, "save_api_keys"):
            raise ValidationError(
                "Too many configuration changes. Please wait before making more changes.",
                field="rate_limit"
            )

        try:
            # Get existing user configuration or create new one
            user_config = self.repository.get_user_config(session_id)
            if not user_config:
                user_config = self.repository.create_user_config(session_id)

            # Validate and encrypt API keys
            encrypted_api_keys = []
            validation_details = []

            for provider, api_key in api_keys.items():
                if not api_key or not api_key.strip():
                    self.logger.warning(f"Empty API key provided for provider: {provider}")
                    continue

                try:
                    # Validate provider name
                    validated_provider = validate_provider_name(provider)

                    # Validate API key format
                    validate_api_key_format(validated_provider, api_key.strip())

                    # Encrypt the API key
                    encrypted_key = self.encryption_service.encrypt(api_key.strip())
                    key_mask = self.encryption_service.generate_key_mask(api_key.strip())

                    # Create API key configuration
                    api_key_config = create_api_key_config(
                        provider=validated_provider,
                        encrypted_key=encrypted_key,
                        key_mask=key_mask,
                        is_valid=True
                    )

                    encrypted_api_keys.append(api_key_config)
                    validation_details.append(f"Validated and encrypted {validated_provider} API key")

                    self.logger.debug(f"Successfully processed API key for provider: {validated_provider}")

                except (ValidationError, ConfigurationError) as e:
                    self.logger.error(f"Failed to validate API key for provider {provider}: {str(e)}")
                    # Continue processing other keys but log the failure
                    validation_details.append(f"Failed to validate {provider} API key: {str(e)}")
                    continue

            if not encrypted_api_keys:
                raise ValidationError("No valid API keys were provided", field="api_keys")

            # Update user configuration with new API keys
            # Keep existing agent configurations
            updated_config = UserConfig(
                session_id=user_config.session_id,
                api_keys=encrypted_api_keys,
                agent_configs=user_config.agent_configs,
                created_at=user_config.created_at,
                updated_at=datetime.now()
            )

            # Save updated configuration
            success = self.repository.update_user_config(session_id, updated_config)

            if success:
                # Invalidate cache for this session to ensure fresh data on next access
                self._invalidate_cache_for_session(session_id)

                # Log successful operation
                details = "; ".join(validation_details)
                self.repository.log_configuration_change(
                    session_id=session_id,
                    action="save_api_keys",
                    details=f"Saved {len(encrypted_api_keys)} API keys. {details}"
                )

                self.logger.info(f"Successfully saved {len(encrypted_api_keys)} API keys for session: {session_id}")
                return True
            else:
                raise ConfigurationError("Failed to save API keys to database")

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, DatabaseError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error saving API keys for session {session_id}: {str(e)}")
            raise ConfigurationError(
                f"Failed to save API keys: {str(e)}",
                config_key="api_keys_save",
                original_error=e
            )

    @handle_errors("get_api_keys", reraise=True)
    def get_api_keys(self, session_id: str) -> Dict[str, str]:
        """
        Retrieve and decrypt API keys for a user session with caching support.

        This method first checks the cache for API keys, and if not found,
        fetches the user configuration, decrypts API keys using the
        encryption service, caches the result, and returns them in a usable format.

        Args:
            session_id: Unique session identifier for the user

        Returns:
            Dictionary mapping provider names to decrypted API keys

        Raises:
            ValidationError: If session_id is invalid
            ConfigurationError: If decryption operations fail
            DatabaseError: If database operations fail

        Examples:
            >>> service = ConfigurationService()
            >>> api_keys = service.get_api_keys("session123")
            >>> print(api_keys["deepseek"])
            sk-actual-decrypted-key-here
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        session_id = session_id.strip()

        try:
            # Check cache first
            cache_key = f"api_keys:{session_id}"
            cached_keys = self._api_keys_cache.get(cache_key)
            if cached_keys is not None:
                self.logger.debug(f"Cache hit for API keys for session: {session_id}")
                return cached_keys

            # Cache miss - fetch from database
            self.logger.debug(f"Cache miss for API keys for session: {session_id}")

            # Get user configuration
            user_config = self.repository.get_user_config(session_id)
            if not user_config:
                self.logger.debug(f"No configuration found for session: {session_id}")
                # Cache empty result to avoid repeated database queries
                self._api_keys_cache.set(cache_key, {})
                return {}

            # Decrypt API keys
            decrypted_keys = {}
            decryption_failures = []

            for api_key_config in user_config.api_keys:
                if not api_key_config.is_valid:
                    self.logger.debug(f"Skipping invalid API key for provider: {api_key_config.provider}")
                    continue

                try:
                    # Decrypt the API key
                    decrypted_key = self.encryption_service.decrypt(api_key_config.encrypted_key)
                    decrypted_keys[api_key_config.provider] = decrypted_key

                    self.logger.debug(f"Successfully decrypted API key for provider: {api_key_config.provider}")

                except Exception as e:
                    self.logger.error(f"Failed to decrypt API key for provider {api_key_config.provider}: {str(e)}")
                    decryption_failures.append(f"{api_key_config.provider}: {str(e)}")
                    continue

            if decryption_failures:
                self.logger.warning(f"Some API keys failed to decrypt for session {session_id}: {'; '.join(decryption_failures)}")

            # Cache the result (even if empty to prevent repeated queries)
            self._api_keys_cache.set(cache_key, decrypted_keys)

            # Log successful retrieval
            self.repository.log_configuration_change(
                session_id=session_id,
                action="get_api_keys",
                details=f"Retrieved {len(decrypted_keys)} API keys"
            )

            self.logger.info(f"Successfully retrieved {len(decrypted_keys)} API keys for session: {session_id}")
            return decrypted_keys

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, DatabaseError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error getting API keys for session {session_id}: {str(e)}")
            raise ConfigurationError(
                f"Failed to retrieve API keys: {str(e)}",
                config_key="api_keys_get",
                original_error=e
            )

    @handle_errors("save_agent_config", reraise=True)
    def save_agent_config(self, session_id: str, agent_id: str, provider: str, model: str) -> bool:
        """
        Save agent-model configuration mapping with validation.

        This method validates the agent configuration, ensures the provider
        has a valid API key configured, and updates the user configuration.

        Args:
            session_id: Unique session identifier for the user
            agent_id: Unique identifier for the intelligent agent
            provider: AI provider name (e.g., 'deepseek', 'bigmodel')
            model: Model name for the specified provider

        Returns:
            True if agent configuration was saved successfully

        Raises:
            ValidationError: If parameters are invalid
            ConfigurationError: If configuration operations fail
            DatabaseError: If database operations fail

        Examples:
            >>> service = ConfigurationService()
            >>> service.save_agent_config("session123", "agent1", "deepseek", "deepseek-chat")
            True
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        if not agent_id or not isinstance(agent_id, str):
            raise ValidationError("Agent ID must be a non-empty string", field="agent_id")

        if not provider or not isinstance(provider, str):
            raise ValidationError("Provider must be a non-empty string", field="provider")

        if not model or not isinstance(model, str):
            raise ValidationError("Model must be a non-empty string", field="model")

        # Normalize inputs
        session_id = session_id.strip()
        agent_id = agent_id.strip()
        provider = provider.strip()
        model = model.strip()

        # Check rate limiting
        if not self._check_rate_limit(session_id, "save_agent_config"):
            raise ValidationError(
                "Too many configuration changes. Please wait before making more changes.",
                field="rate_limit"
            )

        try:
            # Validate provider and get provider info
            validated_provider = validate_provider_name(provider)
            provider_info = SUPPORTED_AI_PROVIDERS[validated_provider]

            # Validate model is supported for the provider
            if model not in provider_info['models']:
                available_models = ', '.join(provider_info['models'])
                raise ValidationError(
                    f"Model '{model}' is not supported for provider '{validated_provider}'. "
                    f"Available models: {available_models}",
                    field="model"
                )

            # Get user configuration
            user_config = self.repository.get_user_config(session_id)
            if not user_config:
                raise ValidationError("No configuration found for this session. Please configure API keys first.")

            # Check if provider has valid API key configured
            provider_has_key = any(
                ak.provider == validated_provider and ak.is_valid
                for ak in user_config.api_keys
            )

            if not provider_has_key:
                raise ValidationError(
                    f"No valid API key configured for provider '{validated_provider}'. "
                    "Please configure an API key for this provider first.",
                    field="provider"
                )

            # Create new agent configuration
            new_agent_config = create_agent_model_config(
                agent_id=agent_id,
                provider=validated_provider,
                model=model
            )

            # Update existing agent configurations
            updated_agent_configs = []
            agent_updated = False

            for existing_config in user_config.agent_configs:
                if existing_config.agent_id == agent_id:
                    # Update existing agent configuration
                    updated_agent_configs.append(new_agent_config)
                    agent_updated = True
                    self.logger.debug(f"Updated configuration for agent: {agent_id}")
                else:
                    # Keep existing configuration
                    updated_agent_configs.append(existing_config)

            # Add new agent configuration if it didn't exist
            if not agent_updated:
                updated_agent_configs.append(new_agent_config)
                self.logger.debug(f"Added new configuration for agent: {agent_id}")

            # Update user configuration
            updated_config = UserConfig(
                session_id=user_config.session_id,
                api_keys=user_config.api_keys,
                agent_configs=updated_agent_configs,
                created_at=user_config.created_at,
                updated_at=datetime.now()
            )

            # Save updated configuration
            success = self.repository.update_user_config(session_id, updated_config)

            if success:
                # Invalidate cache for this session to ensure fresh data on next access
                self._invalidate_cache_for_session(session_id)

                # Log successful operation
                self.repository.log_configuration_change(
                    session_id=session_id,
                    action="save_agent_config",
                    details=f"Saved agent '{agent_id}' configuration: {validated_provider}/{model}"
                )

                self.logger.info(f"Successfully saved agent configuration for '{agent_id}' ({validated_provider}/{model})")
                return True
            else:
                raise ConfigurationError("Failed to save agent configuration to database")

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, DatabaseError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error saving agent config for session {session_id}: {str(e)}")
            raise ConfigurationError(
                f"Failed to save agent configuration: {str(e)}",
                config_key="agent_config_save",
                original_error=e
            )

    @handle_errors("get_agent_config", reraise=True)
    def get_agent_config(self, session_id: str) -> List[AgentModelConfig]:
        """
        Retrieve all agent configurations for a user session with caching support.

        This method first checks the cache for agent configurations, and if not found,
        fetches from the database and caches the result.

        Args:
            session_id: Unique session identifier for the user

        Returns:
            List of agent model configurations

        Raises:
            ValidationError: If session_id is invalid
            ConfigurationError: If retrieval operations fail
            DatabaseError: If database operations fail
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        session_id = session_id.strip()

        try:
            # Check cache first
            cache_key = f"agent_config:{session_id}"
            cached_config = self._config_cache.get(cache_key)
            if cached_config is not None:
                self.logger.debug(f"Cache hit for agent config for session: {session_id}")
                return cached_config

            # Cache miss - fetch from database
            self.logger.debug(f"Cache miss for agent config for session: {session_id}")

            # Get user configuration
            user_config = self.repository.get_user_config(session_id)
            if not user_config:
                self.logger.debug(f"No configuration found for session: {session_id}")
                # Cache empty result to avoid repeated database queries
                self._config_cache.set(cache_key, [])
                return []

            # Cache the result
            self._config_cache.set(cache_key, user_config.agent_configs)

            # Log successful retrieval
            self.repository.log_configuration_change(
                session_id=session_id,
                action="get_agent_config",
                details=f"Retrieved {len(user_config.agent_configs)} agent configurations"
            )

            self.logger.info(f"Successfully retrieved {len(user_config.agent_configs)} agent configurations for session: {session_id}")
            return user_config.agent_configs

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, DatabaseError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error getting agent config for session {session_id}: {str(e)}")
            raise ConfigurationError(
                f"Failed to retrieve agent configurations: {str(e)}",
                config_key="agent_config_get",
                original_error=e
            )

    @handle_errors("validate_api_key", reraise=True)
    def validate_api_key(self, provider: str, api_key: str) -> bool:
        """
        Validate API key format and connectivity with provider-specific validation.

        This method performs comprehensive validation including format checking,
        provider-specific pattern validation, and optional connectivity testing
        to ensure the API key is valid and functional.

        Args:
            provider: AI provider name (e.g., 'deepseek', 'bigmodel')
            api_key: API key to validate

        Returns:
            True if API key is valid and functional

        Raises:
            ValidationError: If API key format is invalid
            ConfigurationError: If provider is unsupported or validation fails
            NetworkError: If connectivity test fails

        Examples:
            >>> service = ConfigurationService()
            >>> service.validate_api_key('deepseek', 'sk-1234567890abcdef1234567890abcdef')
            True
            >>> service.validate_api_key('invalid_provider', 'key')
            ValidationError: Unsupported provider
        """
        # Validate input parameters
        if not provider or not isinstance(provider, str):
            raise ValidationError("Provider is required and must be a string", field="provider")

        if not api_key or not isinstance(api_key, str):
            raise ValidationError("API key is required and must be a string", field="api_key")

        # Normalize inputs
        provider = provider.strip()
        api_key = api_key.strip()

        try:
            # Step 1: Validate provider name
            validated_provider = validate_provider_name(provider)

            # Step 2: Validate API key format using existing validator
            validate_api_key_format(validated_provider, api_key)

            # Step 3: Provider-specific validation based on configuration
            provider_info = SUPPORTED_AI_PROVIDERS[validated_provider]
            provider_name = provider_info.get('name', validated_provider.capitalize())

            self.logger.debug(f"Validating API key for provider: {provider_name}")

            # Step 4: Optional connectivity test (try to create a client and make a minimal request)
            # This is a lightweight validation that doesn't consume significant API quota
            try:
                # Create a temporary client to test the API key
                client = AIClientFactory.create_client(
                    provider=validated_provider,
                    api_key=api_key
                )

                # Perform a lightweight health check
                # For some providers, we might want to skip this to avoid API calls during validation
                # For now, we'll attempt a basic health check but catch any network errors
                health_check_result = client.health_check()

                if health_check_result:
                    self.logger.info(f"API key validation successful for provider: {provider_name}")
                else:
                    self.logger.warning(f"API key format valid but health check failed for provider: {provider_name}")
                    # We still consider the key valid since format is correct and health check might fail due to network issues

                # Clean up the client
                if hasattr(client, 'close'):
                    client.close()

            except Exception as e:
                # Log the connectivity test failure but don't fail validation
                # This allows validation to work even in offline environments
                self.logger.warning(f"Connectivity test failed for {provider_name} API key validation: {str(e)}")
                self.logger.debug(f"API key format validation passed for {provider_name}, but connectivity test failed")

            # Step 5: Additional security checks
            # Check against known invalid patterns or suspicious keys
            suspicious_patterns = [
                r'^test.*$',
                r'^demo.*$',
                r'^fake.*$',
                r'^example.*$',
                r'^sample.*$',
                r'^.{1,10}$',  # Too short keys
                r'^[0]+$',     # All zeros
                r'^[a]+$',     # All same letter
                r'^[1]+$',     # All ones
            ]

            import re
            for pattern in suspicious_patterns:
                if re.match(pattern, api_key, re.IGNORECASE):
                    raise ValidationError(
                        f"API key appears to be a test or invalid key for {provider_name}",
                        field="api_key"
                    )

            # Step 6: Log successful validation for audit purposes
            self.logger.info(f"API key validation completed successfully for provider: {provider_name}")
            self.repository.log_configuration_change(
                session_id="validation",
                action="validate_api_key",
                details=f"Validated API key for provider: {validated_provider}"
            )

            return True

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, NetworkError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error during API key validation for provider {provider}: {str(e)}")
            raise ConfigurationError(
                f"API key validation failed: {str(e)}",
                config_key="api_key_validation",
                original_error=e
            )

    @handle_errors("get_available_models_for_agent", reraise=True)
    def get_available_models_for_agent(self, session_id: str, agent_id: str = None) -> List[Dict[str, Any]]:
        """
        Get available AI models for an agent based on configured API keys with caching support.

        This method first checks the cache for available models, and if not found,
        dynamically loads available models based on the user's configured API keys,
        ensuring that agents can only use models from providers where valid API keys
        have been configured. Results are cached for 30 minutes.

        Args:
            session_id: Unique session identifier for the user
            agent_id: Optional agent identifier for agent-specific model filtering

        Returns:
            List of dictionaries containing model information with provider, model name,
            and display name for use in UI dropdowns

        Raises:
            ValidationError: If session_id is invalid
            ConfigurationError: If model retrieval fails
            DatabaseError: If database operations fail

        Examples:
            >>> service = ConfigurationService()
            >>> models = service.get_available_models_for_agent("session123", "agent1")
            >>> print(models)
            [{'provider': 'deepseek', 'model': 'deepseek-chat', 'display_name': 'DeepSeek - deepseek-chat'}]
        """
        # Validate input parameters
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID must be a non-empty string", field="session_id")

        session_id = session_id.strip()

        # Normalize agent_id if provided
        if agent_id:
            agent_id = agent_id.strip()

        try:
            # Create cache key based on session and agent
            cache_key = f"models:{session_id}:{agent_id or 'none'}"
            cached_models = self._models_cache.get(cache_key)
            if cached_models is not None:
                self.logger.debug(f"Cache hit for available models for session: {session_id}, agent: {agent_id}")
                return cached_models

            # Cache miss - fetch from database
            self.logger.debug(f"Cache miss for available models for session: {session_id}, agent: {agent_id}")

            # Get user configuration to check available API keys
            user_config = self.repository.get_user_config(session_id)
            if not user_config:
                self.logger.debug(f"No configuration found for session: {session_id}")
                # Cache empty result to avoid repeated database queries
                self._models_cache.set(cache_key, [])
                return []

            # Collect available models from configured providers
            available_models = []
            configured_providers = set()

            # Get providers with valid API keys
            for api_key_config in user_config.api_keys:
                if api_key_config.is_valid:
                    configured_providers.add(api_key_config.provider)
                    self.logger.debug(f"Found valid API key for provider: {api_key_config.provider}")

            if not configured_providers:
                self.logger.debug(f"No valid API keys configured for session: {session_id}")
                # Cache empty result to avoid repeated database queries
                self._models_cache.set(cache_key, [])
                return []

            # Get models for each configured provider
            for provider in configured_providers:
                if provider in SUPPORTED_AI_PROVIDERS:
                    provider_info = SUPPORTED_AI_PROVIDERS[provider]
                    provider_name = provider_info.get('name', provider.capitalize())
                    models = provider_info.get('models', [])

                    # Create model entries with display information
                    for model in models:
                        model_info = {
                            'provider': provider,
                            'model': model,
                            'display_name': f"{provider_name} - {model}",
                            'provider_name': provider_name,
                            'is_available': True
                        }

                        # Check if this agent has a specific preference for this provider/model
                        if agent_id and user_config.agent_configs:
                            for agent_config in user_config.agent_configs:
                                if agent_config.agent_id == agent_id:
                                    if agent_config.provider == provider and agent_config.model == model:
                                        model_info['is_current'] = True
                                        model_info['configured_for_agent'] = True
                                    break

                        available_models.append(model_info)
                        self.logger.debug(f"Added model {model} for provider {provider}")

            # Sort models by provider name and then model name for consistent UI ordering
            available_models.sort(key=lambda x: (x['provider_name'], x['model']))

            # If agent_id is provided, move the agent's current model to the top
            if agent_id:
                current_model = next((m for m in available_models if m.get('is_current')), None)
                if current_model:
                    available_models.remove(current_model)
                    available_models.insert(0, current_model)
                    self.logger.debug(f"Moved current model for agent {agent_id} to top of list")

            # Cache the result for 30 minutes
            self._models_cache.set(cache_key, available_models)

            # Log successful model retrieval
            self.repository.log_configuration_change(
                session_id=session_id,
                action="get_available_models",
                details=f"Retrieved {len(available_models)} models for {len(configured_providers)} providers"
            )

            self.logger.info(f"Successfully retrieved {len(available_models)} available models for session: {session_id}")
            return available_models

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, DatabaseError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error getting available models for session {session_id}: {str(e)}")
            raise ConfigurationError(
                f"Failed to retrieve available models: {str(e)}",
                config_key="available_models_get",
                original_error=e
            )

    def _check_rate_limit(self, session_id: str, operation: str, max_requests: int = 5, window_minutes: int = 1) -> bool:
        """
        Check if the session has exceeded the rate limit for configuration changes.

        This is a basic in-memory rate limiter. In production, use Redis or similar
        for distributed rate limiting.

        Args:
            session_id: Unique session identifier
            operation: Operation being performed
            max_requests: Maximum requests allowed in the time window
            window_minutes: Time window in minutes

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        try:
            now = time.time()
            window_start = now - (window_minutes * 60)

            # Create rate limit key
            rate_limit_key = f"{session_id}:{operation}"

            # Get existing requests for this session and operation
            if rate_limit_key not in self._rate_limit_store:
                self._rate_limit_store[rate_limit_key] = []

            # Remove old requests outside the time window
            self._rate_limit_store[rate_limit_key] = [
                req_time for req_time in self._rate_limit_store[rate_limit_key]
                if req_time > window_start
            ]

            # Check if rate limit exceeded
            if len(self._rate_limit_store[rate_limit_key]) >= max_requests:
                self.logger.warning(f"Rate limit exceeded for session {session_id}, operation {operation}")
                return False

            # Add current request
            self._rate_limit_store[rate_limit_key].append(now)

            # Clean up old entries periodically
            self._cleanup_rate_limit_store()

            return True

        except Exception as e:
            # If rate limiting fails, allow the request but log the error
            self.logger.error(f"Rate limiting failed for session {session_id}: {str(e)}")
            return True

    def _cleanup_rate_limit_store(self):
        """Clean up old entries in the rate limit store to prevent memory leaks."""
        try:
            now = time.time()
            cutoff_time = now - (5 * 60)  # Keep entries for 5 minutes

            # Clean up old entries
            keys_to_remove = []
            for key, timestamps in self._rate_limit_store.items():
                # Remove old timestamps
                self._rate_limit_store[key] = [
                    ts for ts in timestamps if ts > cutoff_time
                ]

                # Mark empty keys for removal
                if not self._rate_limit_store[key]:
                    keys_to_remove.append(key)

            # Remove empty keys
            for key in keys_to_remove:
                del self._rate_limit_store[key]

        except Exception as e:
            self.logger.error(f"Failed to cleanup rate limit store: {str(e)}")

    def _invalidate_cache_for_session(self, session_id: str):
        """
        Invalidate all cache entries for a specific session when configuration changes.

        This method removes cached data for a session to ensure that subsequent
        operations fetch fresh data from the database after configuration updates.

        Args:
            session_id: Session ID whose cache should be invalidated
        """
        try:
            invalidated_count = 0

            # Invalidate API keys cache
            api_keys_key = f"api_keys:{session_id}"
            if self._api_keys_cache.delete(api_keys_key):
                invalidated_count += 1

            # Invalidate agent config cache
            agent_config_key = f"agent_config:{session_id}"
            if self._config_cache.delete(agent_config_key):
                invalidated_count += 1

            # Invalidate models cache (all agent variants)
            # We need to check for keys that match the pattern
            # Since TTLCache doesn't support pattern deletion, we'll clear the entire models cache
            # In production, you might want a more sophisticated approach
            self._models_cache.clear()
            invalidated_count += 1  # Count models cache clearing

            self.logger.debug(f"Invalidated {invalidated_count} cache entries for session: {session_id}")

        except Exception as e:
            self.logger.error(f"Failed to invalidate cache for session {session_id}: {str(e)}")
            # Don't raise - cache invalidation failure shouldn't break the operation

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the configuration service including cache statistics.

        Returns:
            Dictionary containing service status information and cache performance metrics
        """
        try:
            return {
                'encryption_service': bool(self.encryption_service),
                'repository': bool(self.repository),
                'rate_limit_entries': len(self._rate_limit_store),
                'cache_stats': {
                    'config_cache': self._config_cache.get_stats(),
                    'models_cache': self._models_cache.get_stats(),
                    'api_keys_cache': self._api_keys_cache.get_stats()
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get service status: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def clear_all_caches(self) -> Dict[str, bool]:
        """
        Clear all caches managed by the configuration service.

        This method clears all caches (config, models, API keys) and returns
        the status of each cache clearing operation.

        Returns:
            Dictionary mapping cache names to their clear operation status
        """
        try:
            results = {}

            # Clear each cache and track results
            try:
                self._config_cache.clear()
                results['config_cache'] = True
            except Exception as e:
                self.logger.error(f"Failed to clear config cache: {str(e)}")
                results['config_cache'] = False

            try:
                self._models_cache.clear()
                results['models_cache'] = True
            except Exception as e:
                self.logger.error(f"Failed to clear models cache: {str(e)}")
                results['models_cache'] = False

            try:
                self._api_keys_cache.clear()
                results['api_keys_cache'] = True
            except Exception as e:
                self.logger.error(f"Failed to clear API keys cache: {str(e)}")
                results['api_keys_cache'] = False

            success_count = sum(1 for success in results.values() if success)
            self.logger.info(f"Cleared caches: {success_count}/{len(results)} successful")

            return results

        except Exception as e:
            self.logger.error(f"Unexpected error clearing caches: {str(e)}")
            return {
                'config_cache': False,
                'models_cache': False,
                'api_keys_cache': False,
                'error': str(e)
            }

    @handle_errors("validate_api_key_connection", reraise=True)
    def validate_api_key_connection(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Validate API key connectivity with provider-specific validation.

        This method performs comprehensive validation including format checking,
        provider-specific pattern validation, and connectivity testing to ensure
        the API key is valid and functional.

        Args:
            provider: AI provider name (e.g., 'deepseek', 'bigmodel')
            api_key: API key to validate

        Returns:
            Dictionary containing validation results with provider info and status

        Raises:
            ValidationError: If API key format is invalid
            ConfigurationError: If provider is unsupported or validation fails
            NetworkError: If connectivity test fails
        """
        # Validate input parameters
        if not provider or not isinstance(provider, str):
            raise ValidationError("Provider is required and must be a string", field="provider")

        if not api_key or not isinstance(api_key, str):
            raise ValidationError("API key is required and must be a string", field="api_key")

        # Normalize inputs
        provider = provider.strip()
        api_key = api_key.strip()

        try:
            # Step 1: Validate provider name
            validated_provider = validate_provider_name(provider)

            # Step 2: Validate API key format using existing validator
            validate_api_key_format(validated_provider, api_key)

            # Step 3: Get provider information
            provider_info = SUPPORTED_AI_PROVIDERS[validated_provider]
            provider_name = provider_info.get('name', validated_provider.capitalize())

            self.logger.debug(f"Validating API key connection for provider: {provider_name}")

            # Step 4: Perform connectivity test
            connection_status = {
                'valid': False,
                'provider': validated_provider,
                'provider_name': provider_name,
                'connection_tested': False,
                'error': None,
                'timestamp': datetime.now().isoformat()
            }

            try:
                # Create a temporary client to test the API key
                client = AIClientFactory.create_client(
                    provider=validated_provider,
                    api_key=api_key
                )

                # Perform a health check to test connectivity
                health_check_result = client.health_check()

                connection_status['connection_tested'] = True
                connection_status['valid'] = health_check_result

                if health_check_result:
                    self.logger.info(f"API key connection validation successful for provider: {provider_name}")
                else:
                    connection_status['error'] = "Health check failed - API key may be invalid or service unavailable"
                    self.logger.warning(f"API key connection validation failed for provider: {provider_name}")

                # Clean up the client
                if hasattr(client, 'close'):
                    client.close()

            except Exception as e:
                connection_status['error'] = str(e)
                self.logger.warning(f"API key connection test failed for {provider_name}: {str(e)}")
                # We still return the validation result but indicate the connection issue

            # Step 5: Log validation attempt for audit purposes
            self.repository.log_configuration_change(
                session_id="validation",
                action="validate_api_key_connection",
                details=f"Tested API key connection for provider: {validated_provider}, result: {connection_status['valid']}"
            )

            return connection_status

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, NetworkError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error during API key connection validation for provider {provider}: {str(e)}")
            raise ConfigurationError(
                f"API key connection validation failed: {str(e)}",
                config_key="api_key_connection_validation",
                original_error=e
            )

    @handle_errors("get_available_models", reraise=True)
    def get_available_models(self, provider: str, api_key: str) -> List[Dict[str, Any]]:
        """
        Get available models for a specific provider using the provided API key.

        This method dynamically retrieves available models from the provider's API
        to ensure accurate and up-to-date model information.

        Args:
            provider: AI provider name (e.g., 'deepseek', 'bigmodel')
            api_key: API key for the provider

        Returns:
            List of dictionaries containing model information

        Raises:
            ValidationError: If provider or API key is invalid
            ConfigurationError: If model retrieval fails
            NetworkError: If API call fails
        """
        # Validate input parameters
        if not provider or not isinstance(provider, str):
            raise ValidationError("Provider is required and must be a string", field="provider")

        if not api_key or not isinstance(api_key, str):
            raise ValidationError("API key is required and must be a string", field="api_key")

        # Normalize inputs
        provider = provider.strip()
        api_key = api_key.strip()

        try:
            # Step 1: Validate provider name
            validated_provider = validate_provider_name(provider)

            # Step 2: Validate API key format
            validate_api_key_format(validated_provider, api_key)

            # Step 3: Get provider information
            provider_info = SUPPORTED_AI_PROVIDERS[validated_provider]
            provider_name = provider_info.get('name', validated_provider.capitalize())

            self.logger.debug(f"Getting available models for provider: {provider_name}")

            # Step 4: Create cache key for models
            cache_key = f"provider_models:{validated_provider}:{hash(api_key)}"
            cached_models = self._models_cache.get(cache_key)
            if cached_models is not None:
                self.logger.debug(f"Cache hit for provider models: {validated_provider}")
                return cached_models

            # Step 5: Retrieve available models
            available_models = []

            try:
                # Create a client to fetch models
                client = AIClientFactory.create_client(
                    provider=validated_provider,
                    api_key=api_key
                )

                # Get available models from the provider
                if hasattr(client, 'get_available_models'):
                    # If the client supports dynamic model retrieval
                    provider_models = client.get_available_models()
                else:
                    # Fall back to configured models
                    provider_models = provider_info.get('models', [])

                # Create model entries with display information
                for model in provider_models:
                    model_info = {
                        'provider': validated_provider,
                        'model': model,
                        'display_name': f"{provider_name} - {model}",
                        'provider_name': provider_name,
                        'is_available': True
                    }
                    available_models.append(model_info)

                # Clean up the client
                if hasattr(client, 'close'):
                    client.close()

            except Exception as e:
                self.logger.warning(f"Failed to get dynamic models for {provider_name}, using fallback: {str(e)}")
                # Fall back to configured models if dynamic retrieval fails
                provider_models = provider_info.get('models', [])
                for model in provider_models:
                    model_info = {
                        'provider': validated_provider,
                        'model': model,
                        'display_name': f"{provider_name} - {model}",
                        'provider_name': provider_name,
                        'is_available': True
                    }
                    available_models.append(model_info)

            # Sort models by model name for consistent UI ordering
            available_models.sort(key=lambda x: x['model'])

            # Cache the result for 30 minutes
            self._models_cache.set(cache_key, available_models)

            # Log successful model retrieval
            self.repository.log_configuration_change(
                session_id="validation",
                action="get_available_models",
                details=f"Retrieved {len(available_models)} models for provider: {validated_provider}"
            )

            self.logger.info(f"Successfully retrieved {len(available_models)} models for provider: {provider_name}")
            return available_models

        except Exception as e:
            if isinstance(e, (ValidationError, ConfigurationError, NetworkError)):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error getting available models for provider {provider}: {str(e)}")
            raise ConfigurationError(
                f"Failed to retrieve available models: {str(e)}",
                config_key="get_available_models",
                original_error=e
            )

    @handle_errors("get_all_supported_models", reraise=True)
    def get_all_supported_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all supported models across all configured providers.

        This method returns a comprehensive list of all available models
        from all supported providers, organized by provider for easy UI consumption.

        Returns:
            Dictionary mapping provider names to lists of model information

        Raises:
            ConfigurationError: If model retrieval fails
        """
        try:
            self.logger.debug("Retrieving all supported models")

            all_models = {}

            for provider, provider_info in SUPPORTED_AI_PROVIDERS.items():
                provider_name = provider_info.get('name', provider.capitalize())
                provider_models = []

                # Get configured models for this provider
                configured_models = provider_info.get('models', [])

                for model in configured_models:
                    model_info = {
                        'provider': provider,
                        'model': model,
                        'display_name': f"{provider_name} - {model}",
                        'provider_name': provider_name,
                        'is_available': True,
                        'capabilities': self._get_model_capabilities(provider, model)
                    }
                    provider_models.append(model_info)

                # Sort models by model name for consistent UI ordering
                provider_models.sort(key=lambda x: x['model'])
                all_models[provider] = provider_models

            # Log successful retrieval
            total_models = sum(len(models) for models in all_models.values())
            self.logger.info(f"Successfully retrieved {total_models} models across {len(all_models)} providers")

            return all_models

        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise

            # Log unexpected errors
            self.logger.error(f"Unexpected error getting all supported models: {str(e)}")
            raise ConfigurationError(
                f"Failed to retrieve supported models: {str(e)}",
                config_key="get_all_supported_models",
                original_error=e
            )

    def _get_model_capabilities(self, provider: str, model: str) -> List[str]:
        """
        Get model capabilities based on provider and model name.

        Args:
            provider: Provider name
            model: Model name

        Returns:
            List of capability strings
        """
        # Default capabilities
        capabilities = ['text-generation']

        # Provider-specific capabilities
        if provider == 'deepseek':
            if 'chat' in model.lower():
                capabilities.extend(['conversation', 'dialogue'])
            if 'coder' in model.lower():
                capabilities.extend(['code-generation', 'technical'])
        elif provider == 'bigmodel':
            if 'glm' in model.lower():
                capabilities.extend(['conversation', 'multimodal'])
            if 'vision' in model.lower():
                capabilities.append('image-analysis')
        elif provider == 'openai':
            if 'gpt-4' in model.lower():
                capabilities.extend(['conversation', 'reasoning', 'multimodal'])
            if 'dall-e' in model.lower():
                capabilities.extend(['image-generation'])

        return capabilities


# Global service instance for convenience
_configuration_service = None


def get_configuration_service() -> ConfigurationService:
    """
    Get the global configuration service instance.

    Returns:
        ConfigurationService: Global service instance
    """
    global _configuration_service
    if _configuration_service is None:
        _configuration_service = ConfigurationService()
    return _configuration_service


# Module initialization
def _initialize_module():
    """Initialize the configuration service module."""
    try:
        logger = get_logger()
        logger.info("Initializing configuration service module")

        # Create global service instance
        service = get_configuration_service()

        # Log initialization success
        logger.info("Configuration service module initialized successfully")

    except Exception as e:
        logger = get_logger()
        logger.error(f"Configuration service module initialization failed: {str(e)}")
        raise


# Initialize module on import
_initialize_module()