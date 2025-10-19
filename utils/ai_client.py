"""
AI API Client module for podcast generation system.

This module provides a unified interface for interacting with multiple AI providers
including DeepSeek and BigModel APIs. It handles authentication, request formatting,
response parsing, and comprehensive error handling with retry logic.

Purpose: Abstract AI API interactions and provide consistent interface across providers.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import configuration and error handling
try:
    from config import (
        DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL,
        BIGMODEL_API_KEY, BIGMODEL_API_BASE, BIGMODEL_MODEL,
        AI_SERVICE_TIMEOUT, AI_MAX_RETRIES, AI_RETRY_DELAY
    )
except (ValueError, ImportError):
    # Fallback defaults for testing/development
    DEEPSEEK_API_KEY = ''
    DEEPSEEK_API_BASE = 'https://api.deepseek.com/v1'
    DEEPSEEK_MODEL = 'deepseek-chat'
    BIGMODEL_API_KEY = ''
    BIGMODEL_API_BASE = 'https://open.bigmodel.cn/api/paas/v4'
    BIGMODEL_MODEL = 'glm-4'
    AI_SERVICE_TIMEOUT = 60
    AI_MAX_RETRIES = 3
    AI_RETRY_DELAY = 1.0

from .error_handler import (
    AIAPIError, NetworkError, ConfigurationError,
    get_logger, ai_api_retry, handle_errors
)


@dataclass
class AIMessage:
    """Represents a message in AI conversation."""
    role: str  # 'system', 'user', 'assistant'
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary format."""
        return {'role': self.role, 'content': self.content}


@dataclass
class AIResponse:
    """Represents a response from AI API."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    response_time: float
    provider: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            'content': self.content,
            'model': self.model,
            'usage': self.usage,
            'finish_reason': self.finish_reason,
            'response_time': self.response_time,
            'provider': self.provider
        }


class BaseAIClient(ABC):
    """Abstract base class for AI API clients."""

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = None):
        """
        Initialize AI client.

        Args:
            api_key: API key for authentication
            base_url: Base URL for API endpoints
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout or AI_SERVICE_TIMEOUT
        self.logger = get_logger()

        # Configure HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PodcastGeneration/1.0'
        })

    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get provider-specific authentication headers."""
        pass

    @abstractmethod
    def _format_messages(self, messages: List[AIMessage]) -> Dict[str, Any]:
        """Format messages for specific API provider."""
        pass

    @abstractmethod
    def _parse_response(self, response_data: Dict[str, Any], response_time: float) -> AIResponse:
        """Parse API response into AIResponse object."""
        pass

    @abstractmethod
    def _extract_error_info(self, response_data: Dict[str, Any]) -> tuple[str, int, Dict[str, Any]]:
        """Extract error information from failed API response."""
        pass

    def _validate_config(self) -> None:
        """Validate client configuration."""
        if not self.api_key:
            raise ConfigurationError(
                f"API key is required for {self.__class__.__name__}",
                config_key='api_key'
            )

        if not self.base_url:
            raise ConfigurationError(
                f"Base URL is required for {self.__class__.__name__}",
                config_key='base_url'
            )

        if not self.model:
            raise ConfigurationError(
                f"Model name is required for {self.__class__.__name__}",
                config_key='model'
            )

    @ai_api_retry()
    @handle_errors("AI API call", reraise=True)
    def generate_response(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """
        Generate response from AI model.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            **kwargs: Additional provider-specific parameters

        Returns:
            AIResponse object with generated content

        Raises:
            AIAPIError: If API call fails
            NetworkError: If network connection fails
        """
        # Validate configuration
        self._validate_config()

        # Validate input
        if not messages:
            raise AIAPIError("Messages list cannot be empty", api_provider=self.__class__.__name__)

        # Prepare request data
        request_data = self._format_messages(messages)
        request_data.update({
            'temperature': temperature,
            **kwargs
        })

        if max_tokens:
            request_data['max_tokens'] = max_tokens
        if top_p:
            request_data['top_p'] = top_p

        # Make API call
        start_time = time.time()
        try:
            headers = self._get_auth_headers()
            endpoint = f"{self.base_url}/chat/completions"

            self.logger.debug(f"Making API call to {endpoint}")
            response = self.session.post(
                endpoint,
                headers=headers,
                json=request_data,
                timeout=self.timeout
            )

            response_time = time.time() - start_time

            # Handle response
            if response.status_code == 200:
                response_data = response.json()
                return self._parse_response(response_data, response_time)
            else:
                # Parse error response
                try:
                    error_data = response.json()
                except ValueError:
                    error_data = {'error': {'message': response.text}}

                error_message, status_code, response_details = self._extract_error_info(error_data)

                raise AIAPIError(
                    error_message,
                    api_provider=self.__class__.__name__,
                    status_code=response.status_code or status_code,
                    response_data=response_details
                )

        except requests.exceptions.Timeout:
            raise NetworkError(
                f"Request timeout after {self.timeout}s",
                timeout=self.timeout,
                url=f"{self.base_url}/chat/completions"
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Connection error: {str(e)}",
                url=f"{self.base_url}/chat/completions"
            )
        except requests.exceptions.RequestException as e:
            raise NetworkError(
                f"Request failed: {str(e)}",
                url=f"{self.base_url}/chat/completions"
            )
        except json.JSONDecodeError as e:
            raise AIAPIError(
                f"Invalid JSON response: {str(e)}",
                api_provider=self.__class__.__name__,
                response_data={'raw_response': response.text[:500]}
            )

    def health_check(self) -> bool:
        """
        Check if the API service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            test_message = AIMessage(role="user", content="Hello")
            response = self.generate_response(
                messages=[test_message],
                max_tokens=10
            )
            return bool(response.content)
        except Exception as e:
            self.logger.warning(f"Health check failed for {self.__class__.__name__}: {str(e)}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.

        Returns:
            Dictionary with model information
        """
        return {
            'provider': self.__class__.__name__,
            'model': self.model,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'has_api_key': bool(self.api_key)
        }

    def close(self):
        """Close HTTP session."""
        if self.session:
            self.session.close()


class DeepSeekClient(BaseAIClient):
    """DeepSeek API client implementation."""

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get DeepSeek authentication headers."""
        return {'Authorization': f'Bearer {self.api_key}'}

    def _format_messages(self, messages: List[AIMessage]) -> Dict[str, Any]:
        """Format messages for DeepSeek API."""
        return {
            'model': self.model,
            'messages': [msg.to_dict() for msg in messages]
        }

    def _parse_response(self, response_data: Dict[str, Any], response_time: float) -> AIResponse:
        """Parse DeepSeek API response."""
        try:
            choice = response_data['choices'][0]
            message = choice['message']['content']

            return AIResponse(
                content=message,
                model=response_data.get('model', self.model),
                usage=response_data.get('usage', {}),
                finish_reason=choice.get('finish_reason', 'unknown'),
                response_time=response_time,
                provider='DeepSeek'
            )
        except (KeyError, IndexError) as e:
            raise AIAPIError(
                f"Invalid response format: {str(e)}",
                api_provider='DeepSeek',
                response_data=response_data
            )

    def _extract_error_info(self, response_data: Dict[str, Any]) -> tuple[str, int, Dict[str, Any]]:
        """Extract error information from DeepSeek API response."""
        error_info = response_data.get('error', {})
        message = error_info.get('message', 'Unknown error')
        code = error_info.get('code', 'unknown')

        return f"DeepSeek API error ({code}): {message}", 500, response_data


class BigModelClient(BaseAIClient):
    """BigModel (智谱AI) API client implementation."""

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get BigModel authentication headers."""
        return {'Authorization': f'Bearer {self.api_key}'}

    def _format_messages(self, messages: List[AIMessage]) -> Dict[str, Any]:
        """Format messages for BigModel API."""
        return {
            'model': self.model,
            'messages': [msg.to_dict() for msg in messages]
        }

    def _parse_response(self, response_data: Dict[str, Any], response_time: float) -> AIResponse:
        """Parse BigModel API response."""
        try:
            choice = response_data['choices'][0]
            message = choice['message']['content']

            return AIResponse(
                content=message,
                model=response_data.get('model', self.model),
                usage=response_data.get('usage', {}),
                finish_reason=choice.get('finish_reason', 'unknown'),
                response_time=response_time,
                provider='BigModel'
            )
        except (KeyError, IndexError) as e:
            raise AIAPIError(
                f"Invalid response format: {str(e)}",
                api_provider='BigModel',
                response_data=response_data
            )

    def _extract_error_info(self, response_data: Dict[str, Any]) -> tuple[str, int, Dict[str, Any]]:
        """Extract error information from BigModel API response."""
        error_info = response_data.get('error', {})
        message = error_info.get('message', 'Unknown error')
        code = error_info.get('code', 'unknown')

        return f"BigModel API error ({code}): {message}", 500, response_data


class AIClientFactory:
    """Factory class for creating AI clients."""

    _clients = {
        'deepseek': DeepSeekClient,
        'bigmodel': BigModelClient
    }

    @classmethod
    def create_client(cls, provider: str, session_id: str = None, **kwargs) -> BaseAIClient:
        """
        Create an AI client for the specified provider.

        Args:
            provider: Name of the AI provider ('deepseek' or 'bigmodel')
            session_id: User session ID for retrieving user-specific API keys
            **kwargs: Additional configuration parameters

        Returns:
            Configured AI client instance

        Raises:
            ConfigurationError: If provider is not supported or configuration is invalid
        """
        provider = provider.lower()

        if provider not in cls._clients:
            raise ConfigurationError(
                f"Unsupported AI provider: {provider}. "
                f"Supported providers: {list(cls._clients.keys())}"
            )

        client_class = cls._clients[provider]

        # Try to get user-specific API key first
        api_key = None
        if session_id:
            api_key = cls._get_user_api_key(session_id, provider)

        # Fallback to environment variable for backward compatibility
        if not api_key:
            if provider == 'deepseek':
                api_key = DEEPSEEK_API_KEY
            elif provider == 'bigmodel':
                api_key = BIGMODEL_API_KEY

        # Get provider-specific configuration
        if provider == 'deepseek':
            base_url = kwargs.get('base_url', DEEPSEEK_API_BASE)
            model = kwargs.get('model', DEEPSEEK_MODEL)
        elif provider == 'bigmodel':
            base_url = kwargs.get('base_url', BIGMODEL_API_BASE)
            model = kwargs.get('model', BIGMODEL_MODEL)

        return client_class(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=kwargs.get('timeout', AI_SERVICE_TIMEOUT)
        )

    @classmethod
    def _get_user_api_key(cls, session_id: str, provider: str) -> Optional[str]:
        """
        Get user-specific API key from configuration service.

        Args:
            session_id: User session ID
            provider: AI provider name

        Returns:
            API key if found, None otherwise
        """
        try:
            # Import configuration service
            from .configuration_service import get_configuration_service

            # Get configuration service instance
            config_service = get_configuration_service()

            # Get API keys for the session
            api_keys = config_service.get_api_keys(session_id)

            # Return API key for the specific provider
            return api_keys.get(provider)

        except Exception as e:
            # Log the error but don't fail - we'll use environment variable fallback
            logger.warning(f"Failed to get user API key for {provider} (session: {session_id}): {str(e)}")
            return None

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get list of available AI providers.

        Returns:
            List of provider names
        """
        return list(cls._clients.keys())

    @classmethod
    def get_configured_providers(cls) -> List[str]:
        """
        Get list of providers with valid API keys configured.

        Returns:
            List of provider names with API keys
        """
        configured = []

        if DEEPSEEK_API_KEY:
            configured.append('deepseek')

        if BIGMODEL_API_KEY:
            configured.append('bigmodel')

        return configured


class UnifiedAIClient:
    """
    Unified interface for multiple AI providers with automatic failover.
    """

    def __init__(self, preferred_providers: List[str] = None):
        """
        Initialize unified AI client.

        Args:
            preferred_providers: List of providers in order of preference
        """
        self.logger = get_logger()

        # Determine available providers
        configured_providers = AIClientFactory.get_configured_providers()

        if not configured_providers:
            raise ConfigurationError(
                "No AI providers are configured. "
                "Please set DEEPSEEK_API_KEY or BIGMODEL_API_KEY environment variables."
            )

        # Use preferred providers or configured providers
        if preferred_providers:
            self.providers = [p for p in preferred_providers if p in configured_providers]
            if not self.providers:
                self.logger.warning(
                    f"None of preferred providers {preferred_providers} are configured. "
                    f"Using available providers: {configured_providers}"
                )
                self.providers = configured_providers
        else:
            self.providers = configured_providers

        # Initialize clients
        self.clients = {}
        for provider in self.providers:
            try:
                self.clients[provider] = AIClientFactory.create_client(provider)
                self.logger.info(f"Initialized AI client for provider: {provider}")
            except Exception as e:
                self.logger.error(f"Failed to initialize client for {provider}: {str(e)}")

        if not self.clients:
            raise ConfigurationError("Failed to initialize any AI clients")

    def generate_response(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        allow_failover: bool = True,
        **kwargs
    ) -> AIResponse:
        """
        Generate response using available AI providers with failover.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            allow_failover: Whether to try other providers if primary fails
            **kwargs: Additional provider-specific parameters

        Returns:
            AIResponse object with generated content

        Raises:
            AIAPIError: If all providers fail
        """
        last_exception = None

        for provider in self.providers:
            if provider not in self.clients:
                continue

            try:
                self.logger.debug(f"Attempting to generate response using {provider}")
                client = self.clients[provider]
                response = client.generate_response(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    **kwargs
                )

                self.logger.info(f"Successfully generated response using {provider}")
                return response

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Failed to generate response using {provider}: {str(e)}")

                if not allow_failover:
                    break

        # All providers failed
        if last_exception:
            raise AIAPIError(
                f"All AI providers failed. Last error: {str(last_exception)}",
                api_provider="unified",
                original_error=last_exception
            )
        else:
            raise AIAPIError("No AI providers available")

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all configured providers.

        Returns:
            Dictionary mapping provider names to health status
        """
        results = {}

        for provider, client in self.clients.items():
            try:
                results[provider] = client.health_check()
            except Exception as e:
                self.logger.error(f"Health check failed for {provider}: {str(e)}")
                results[provider] = False

        return results

    def get_provider_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all configured providers.

        Returns:
            List of provider information dictionaries
        """
        info = []

        for provider, client in self.clients.items():
            try:
                provider_info = client.get_model_info()
                provider_info['healthy'] = client.health_check()
                info.append(provider_info)
            except Exception as e:
                self.logger.error(f"Failed to get info for {provider}: {str(e)}")
                info.append({
                    'provider': provider,
                    'error': str(e),
                    'healthy': False
                })

        return info

    def close_all(self):
        """Close all client sessions."""
        for client in self.clients.values():
            try:
                client.close()
            except Exception as e:
                self.logger.error(f"Error closing client: {str(e)}")


# Convenience functions for easy usage
def create_ai_client(provider: str = None, **kwargs) -> Union[BaseAIClient, UnifiedAIClient]:
    """
    Create an AI client instance.

    Args:
        provider: Specific provider to use, or None for unified client
        **kwargs: Additional configuration parameters

    Returns:
        AI client instance
    """
    if provider:
        return AIClientFactory.create_client(provider, **kwargs)
    else:
        return UnifiedAIClient(**kwargs)


def generate_podcast_dialogue(
    messages: List[AIMessage],
    provider: str = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> AIResponse:
    """
    Convenience function for generating podcast dialogue.

    Args:
        messages: List of conversation messages
        provider: Specific provider to use, or None for automatic selection
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        **kwargs: Additional parameters

    Returns:
        AIResponse with generated dialogue
    """
    client = create_ai_client(provider)
    try:
        return client.generate_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    finally:
        if hasattr(client, 'close'):
            client.close()
        elif hasattr(client, 'close_all'):
            client.close_all()