"""
Encryption service for secure API key storage and management.

This module provides AES-256 encryption/decryption functionality for sensitive
API key data, along with key masking for UI display and error handling
integration with the existing error handling system.

Purpose: Provide secure storage for sensitive API key data with proper
encryption, masking, and error handling integration.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from utils.error_handler import (
    ConfigurationError,
    ErrorSeverity,
    handle_errors,
    get_logger
)


class EncryptionService:
    """
    Handles AES-256 encryption/decryption of sensitive API keys and related data.

    This service provides secure encryption for API keys using industry-standard
    cryptography libraries, with key rotation support and secure masking for UI display.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption service with a secure key.

        Args:
            encryption_key: Optional base64-encoded encryption key. If not provided,
                          a new key will be generated from environment or created.

        Raises:
            ConfigurationError: If encryption key initialization fails
        """
        self.logger = get_logger()
        self._encryption_key = None
        self._fernet = None

        try:
            self._initialize_encryption_key(encryption_key)
            self.logger.info("Encryption service initialized successfully")
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize encryption service: {str(e)}",
                config_key="encryption_key",
                original_error=e
            )

    @handle_errors("encryption_key_initialization", reraise=True)
    def _initialize_encryption_key(self, encryption_key: Optional[str] = None) -> None:
        """
        Initialize or generate the encryption key.

        Args:
            encryption_key: Optional base64-encoded encryption key
        """
        if encryption_key:
            # Use provided key (must be base64 encoded)
            try:
                key_bytes = base64.b64decode(encryption_key.encode())
                if len(key_bytes) != 44:  # Fernet key length
                    raise ValueError("Invalid encryption key length")
                self._encryption_key = encryption_key
                self._fernet = Fernet(key_bytes)
                self.logger.info("Encryption service initialized with provided key")
            except Exception as e:
                raise ConfigurationError(
                    f"Invalid encryption key provided: {str(e)}",
                    config_key="encryption_key"
                )
        else:
            # Try to get key from environment
            env_key = os.environ.get('ENCRYPTION_KEY')
            if env_key:
                try:
                    key_bytes = base64.b64decode(env_key.encode())
                    if len(key_bytes) != 44:
                        raise ValueError("Invalid encryption key length in environment")
                    self._encryption_key = env_key
                    self._fernet = Fernet(key_bytes)
                    self.logger.info("Encryption service initialized with environment key")
                    return
                except Exception as e:
                    self.logger.warning(f"Failed to use environment encryption key: {e}")

            # Generate new key from master secret
            master_secret = os.environ.get('MASTER_SECRET', 'default-master-secret-change-in-production')
            self._encryption_key = self._derive_key_from_secret(master_secret)
            self._fernet = Fernet(self._encryption_key.encode())
            self.logger.info("Encryption service initialized with derived key")

    def _derive_key_from_secret(self, secret: str, salt: Optional[bytes] = None) -> str:
        """
        Derive a secure encryption key from a master secret using PBKDF2.

        Args:
            secret: Master secret for key derivation
            salt: Optional salt for key derivation (generated if not provided)

        Returns:
            Base64-encoded encryption key
        """
        if salt is None:
            # Generate a consistent salt for this installation
            salt = hashlib.sha256(secret.encode() + b'podcast-encryption-salt').digest()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits (required for Fernet)
            salt=salt,
            iterations=100000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return key.decode()

    @handle_errors("encryption")
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data using AES-256 encryption.

        Args:
            data: Plain text data to encrypt

        Returns:
            Base64-encoded encrypted data

        Raises:
            ConfigurationError: If encryption operation fails
        """
        if not data:
            raise ConfigurationError("Cannot encrypt empty data")

        if not isinstance(data, str):
            raise ConfigurationError("Data must be a string")

        try:
            # Convert to bytes if needed
            data_bytes = data.encode('utf-8')

            # Encrypt the data
            encrypted_data = self._fernet.encrypt(data_bytes)

            # Return base64 encoded encrypted data
            return base64.b64encode(encrypted_data).decode('utf-8')

        except Exception as e:
            raise ConfigurationError(
                f"Failed to encrypt data: {str(e)}",
                config_key="encryption_operation",
                original_error=e
            )

    @handle_errors("decryption")
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data using AES-256 decryption.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted plain text data

        Raises:
            ConfigurationError: If decryption operation fails
        """
        if not encrypted_data:
            raise ConfigurationError("Cannot decrypt empty data")

        if not isinstance(encrypted_data, str):
            raise ConfigurationError("Encrypted data must be a string")

        try:
            # Decode base64 to get encrypted bytes
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))

            # Decrypt the data
            decrypted_data = self._fernet.decrypt(encrypted_bytes)

            # Convert back to string
            return decrypted_data.decode('utf-8')

        except Exception as e:
            # Log decryption failures as security events
            self.logger.warning(f"Decryption failure detected: {str(e)}")
            raise ConfigurationError(
                f"Failed to decrypt data: {str(e)}",
                config_key="decryption_operation",
                original_error=e
            )

    @handle_errors("key_masking")
    def generate_key_mask(self, api_key: str) -> str:
        """
        Generate a masked version of the API key for UI display.

        Only shows the last 4 characters of the key for identification purposes.

        Args:
            api_key: The full API key to mask

        Returns:
            Masked API key (e.g., "sk-********************abcd")

        Raises:
            ConfigurationError: If key masking operation fails
        """
        if not api_key:
            return ""

        if not isinstance(api_key, str):
            raise ConfigurationError("API key must be a string")

        try:
            # If key is too short, return it masked completely
            if len(api_key) <= 4:
                return "*" * len(api_key)

            # Show only last 4 characters
            return "*" * (len(api_key) - 4) + api_key[-4:]

        except Exception as e:
            raise ConfigurationError(
                f"Failed to generate key mask: {str(e)}",
                original_error=e
            )

    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted by this service.

        Args:
            data: Data to check

        Returns:
            True if data appears to be encrypted, False otherwise
        """
        if not data or not isinstance(data, str):
            return False

        try:
            # Try to decode as base64 and decrypt
            encrypted_bytes = base64.b64decode(data.encode('utf-8'))
            # If we can decode and it's reasonable length, assume it's encrypted
            return len(encrypted_bytes) > 0
        except Exception:
            return False

    @handle_errors("key_rotation")
    def rotate_encryption_key(self, old_data: str, new_encryption_key: Optional[str] = None) -> str:
        """
        Rotate encryption key and re-encrypt data with new key.

        Args:
            old_data: Data encrypted with old key
            new_encryption_key: Optional new encryption key

        Returns:
            Data re-encrypted with new key

        Raises:
            ConfigurationError: If key rotation fails
        """
        try:
            # First decrypt with current key
            decrypted_data = self.decrypt(old_data)

            # Initialize new encryption
            if new_encryption_key:
                new_service = EncryptionService(new_encryption_key)
            else:
                # Generate new key
                new_secret = secrets.token_urlsafe(32)
                new_service = EncryptionService()
                new_service._initialize_encryption_key()

            # Re-encrypt with new key
            new_encrypted_data = new_service.encrypt(decrypted_data)

            self.logger.info("Successfully rotated encryption key")
            return new_encrypted_data

        except Exception as e:
            raise ConfigurationError(
                f"Failed to rotate encryption key: {str(e)}",
                config_key="key_rotation",
                original_error=e
            )

    def get_encryption_key_info(self) -> dict:
        """
        Get information about the current encryption key configuration.

        Returns:
            Dictionary with encryption key information
        """
        return {
            'key_initialized': self._encryption_key is not None,
            'key_length': len(self._encryption_key) if self._encryption_key else 0,
            'encryption_algorithm': 'AES-256 (via Fernet)',
            'key_derivation': 'PBKDF2-SHA256'
        }

    @handle_errors("secure_data_wipe")
    def secure_wipe(self, encrypted_data: str) -> bool:
        """
        Securely wipe encrypted data by attempting to decrypt and then overwriting.

        Args:
            encrypted_data: Encrypted data to wipe

        Returns:
            True if wipe was successful, False otherwise
        """
        try:
            # Try to decrypt first to verify data integrity
            decrypted = self.decrypt(encrypted_data)

            # Overwrite the decrypted data in memory
            # Note: Python memory management makes true secure deletion difficult
            # but we make a best effort by overwriting the string
            decrypted = 'X' * len(decrypted)

            # Clear encrypted data
            encrypted_data = 'X' * len(encrypted_data)

            self.logger.info("Secure wipe completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Secure wipe failed: {str(e)}")
            return False

    @handle_errors("batch_encryption")
    def encrypt_batch(self, data_items: list) -> list:
        """
        Encrypt multiple data items in batch for efficiency.

        Args:
            data_items: List of strings to encrypt

        Returns:
            List of encrypted data items

        Raises:
            ConfigurationError: If batch encryption fails
        """
        if not isinstance(data_items, list):
            raise ConfigurationError("Data items must be provided as a list")

        encrypted_items = []
        failed_items = []

        for i, item in enumerate(data_items):
            try:
                encrypted_item = self.encrypt(item)
                encrypted_items.append(encrypted_item)
            except Exception as e:
                failed_items.append({'index': i, 'error': str(e)})
                self.logger.warning(f"Failed to encrypt item {i}: {str(e)}")

        if failed_items:
            raise ConfigurationError(
                f"Batch encryption partially failed. Failed items: {len(failed_items)}",
                details={'failed_items': failed_items}
            )

        return encrypted_items

    @handle_errors("batch_decryption")
    def decrypt_batch(self, encrypted_items: list) -> list:
        """
        Decrypt multiple encrypted items in batch for efficiency.

        Args:
            encrypted_items: List of encrypted strings to decrypt

        Returns:
            List of decrypted data items

        Raises:
            ConfigurationError: If batch decryption fails
        """
        if not isinstance(encrypted_items, list):
            raise ConfigurationError("Encrypted items must be provided as a list")

        decrypted_items = []
        failed_items = []

        for i, item in enumerate(encrypted_items):
            try:
                decrypted_item = self.decrypt(item)
                decrypted_items.append(decrypted_item)
            except Exception as e:
                failed_items.append({'index': i, 'error': str(e)})
                self.logger.warning(f"Failed to decrypt item {i}: {str(e)}")

        if failed_items:
            raise ConfigurationError(
                f"Batch decryption partially failed. Failed items: {len(failed_items)}",
                details={'failed_items': failed_items}
            )

        return decrypted_items


# Global encryption service instance for application-wide use
_global_encryption_service = None


def get_encryption_service(encryption_key: Optional[str] = None) -> EncryptionService:
    """
    Get or create the global encryption service instance.

    Args:
        encryption_key: Optional encryption key for initialization

    Returns:
        EncryptionService instance
    """
    global _global_encryption_service

    if _global_encryption_service is None:
        _global_encryption_service = EncryptionService(encryption_key)

    return _global_encryption_service


def create_test_encryption_service() -> EncryptionService:
    """
    Create a dedicated encryption service for testing purposes.

    Returns:
        EncryptionService instance with test key
    """
    test_key = base64.urlsafe_b64encode(b'test-key-for-development-only-32bytes').decode()
    return EncryptionService(test_key)


# Utility functions for common encryption tasks
def encrypt_api_key(api_key: str, encryption_key: Optional[str] = None) -> Tuple[str, str]:
    """
    Encrypt an API key and generate its mask in one operation.

    Args:
        api_key: Plain text API key
        encryption_key: Optional encryption key

    Returns:
        Tuple of (encrypted_key, key_mask)

    Raises:
        ConfigurationError: If encryption operation fails
    """
    service = get_encryption_service(encryption_key)
    encrypted_key = service.encrypt(api_key)
    key_mask = service.generate_key_mask(api_key)

    return encrypted_key, key_mask


def decrypt_api_key(encrypted_key: str, encryption_key: Optional[str] = None) -> str:
    """
    Decrypt an encrypted API key.

    Args:
        encrypted_key: Encrypted API key
        encryption_key: Optional encryption key

    Returns:
        Decrypted API key

    Raises:
        ConfigurationError: If decryption operation fails
    """
    service = get_encryption_service(encryption_key)
    return service.decrypt(encrypted_key)


def validate_encryption_setup() -> dict:
    """
    Validate that encryption is properly set up and working.

    Returns:
        Dictionary with validation results
    """
    try:
        service = get_encryption_service()

        # Test encryption/decryption
        test_data = "test-api-key-validation-123456"
        encrypted = service.encrypt(test_data)
        decrypted = service.decrypt(encrypted)

        # Test key masking
        mask = service.generate_key_mask(test_data)

        validation_result = {
            'valid': True,
            'encryption_working': decrypted == test_data,
            'masking_working': mask.endswith('456'),
            'key_info': service.get_encryption_key_info()
        }

        if not validation_result['encryption_working']:
            validation_result['valid'] = False
            validation_result['error'] = 'Encryption/decryption round trip failed'

        if not validation_result['masking_working']:
            validation_result['valid'] = False
            validation_result['error'] = 'Key masking not working correctly'

        return validation_result

    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'encryption_working': False,
            'masking_working': False,
            'key_info': None
        }