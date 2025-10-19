"""
Input validation utilities for podcast generation system.

This module provides comprehensive validation and sanitization functions
for all user input data to ensure security, data integrity, and API safety.
"""

import re
import html
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlparse

# Import configuration with fallback defaults for testing
try:
    from config import (
        MAX_INPUT_LENGTH, MIN_PARTICIPANTS, MAX_PARTICIPANTS,
        MIN_CONVERSATION_ROUNDS, MAX_CONVERSATION_ROUNDS
    )
except (ValueError, ImportError):
    # Fallback defaults for testing/development
    MAX_INPUT_LENGTH = 1000
    MIN_PARTICIPANTS = 2
    MAX_PARTICIPANTS = 6
    MIN_CONVERSATION_ROUNDS = 3
    MAX_CONVERSATION_ROUNDS = 20

# Import models for validation
from utils.models import Gender, Language, Character

# Import config for API provider validation
try:
    from config import SUPPORTED_AI_PROVIDERS
except (ValueError, ImportError):
    # Fallback defaults for testing/development
    SUPPORTED_AI_PROVIDERS = {
        'deepseek': {
            'name': 'DeepSeek',
            'key_prefix': 'sk-',
            'min_length': 20,
            'models': ['deepseek-chat', 'deepseek-coder']
        },
        'bigmodel': {
            'name': 'BigModel',
            'key_prefix': '',
            'min_length': 32,
            'models': ['glm-4', 'glm-3-turbo']
        }
    }


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: str = None):
        """
        Initialize validation error.

        Args:
            message: Error message describing the validation failure
            field: Optional field name that caused the error
        """
        super().__init__(message)
        self.message = message
        self.field = field


def sanitize_text(text: str, max_length: int = None) -> str:
    """
    Sanitize text input for API safety and data integrity.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (defaults to config MAX_INPUT_LENGTH)

    Returns:
        Sanitized text safe for API usage

    Raises:
        ValidationError: If text exceeds maximum length
    """
    if text is None:
        return ""

    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)

    # Set default max_length from config if not provided
    if max_length is None:
        max_length = MAX_INPUT_LENGTH

    # Check length
    if len(text) > max_length:
        raise ValidationError(
            f"Text exceeds maximum length of {max_length} characters"
        )

    # Remove null bytes
    text = text.replace('\x00', '')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Escape HTML entities to prevent XSS
    text = html.escape(text)

    # Remove potentially dangerous characters for API calls
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    return text


def validate_character_count(count: Union[str, int]) -> int:
    """
    Validate participant count is within reasonable limits.

    Args:
        count: Number of participants to validate

    Returns:
        Validated integer count

    Raises:
        ValidationError: If count is invalid or out of range
    """
    if count is None:
        raise ValidationError("Participant count is required")

    try:
        # Convert to integer if string
        if isinstance(count, str):
            count = int(count.strip())
        elif not isinstance(count, int):
            count = int(count)
    except (ValueError, TypeError):
        raise ValidationError("Participant count must be a valid integer")

    # Check range
    if count < MIN_PARTICIPANTS:
        raise ValidationError(
            f"Minimum {MIN_PARTICIPANTS} participants required"
        )

    if count > MAX_PARTICIPANTS:
        raise ValidationError(
            f"Maximum {MAX_PARTICIPANTS} participants allowed"
        )

    return count


def validate_conversation_rounds(rounds: Union[str, int]) -> int:
    """
    Validate conversation rounds is within reasonable limits.

    Args:
        rounds: Number of conversation rounds to validate

    Returns:
        Validated integer rounds

    Raises:
        ValidationError: If rounds is invalid or out of range
    """
    if rounds is None:
        raise ValidationError("Conversation rounds is required")

    try:
        # Convert to integer if string
        if isinstance(rounds, str):
            rounds = int(rounds.strip())
        elif not isinstance(rounds, int):
            rounds = int(rounds)
    except (ValueError, TypeError):
        raise ValidationError("Conversation rounds must be a valid integer")

    # Check range
    if rounds < MIN_CONVERSATION_ROUNDS:
        raise ValidationError(
            f"Minimum {MIN_CONVERSATION_ROUNDS} conversation rounds required"
        )

    if rounds > MAX_CONVERSATION_ROUNDS:
        raise ValidationError(
            f"Maximum {MAX_CONVERSATION_ROUNDS} conversation rounds allowed"
        )

    return rounds


def validate_gender(gender: str) -> Gender:
    """
    Validate gender input and convert to Gender enum.

    Args:
        gender: Gender string to validate

    Returns:
        Gender enum value

    Raises:
        ValidationError: If gender is invalid
    """
    if gender is None:
        raise ValidationError("Gender is required")

    # Sanitize input
    gender = sanitize_text(gender.lower().strip())

    if not gender:
        raise ValidationError("Gender cannot be empty")

    # Try to match with enum values
    try:
        return Gender(gender)
    except ValueError:
        # Check for common variations
        gender_mapping = {
            'm': Gender.MALE,
            'male': Gender.MALE,
            'man': Gender.MALE,
            'men': Gender.MALE,
            'f': Gender.FEMALE,
            'female': Gender.FEMALE,
            'woman': Gender.FEMALE,
            'women': Gender.FEMALE,
            'other': Gender.OTHER,
            'non-binary': Gender.OTHER,
            'nonbinary': Gender.OTHER,
            # Chinese gender support
            '男性': Gender.MALE,
            '男': Gender.MALE,
            '女性': Gender.FEMALE,
            '女': Gender.FEMALE,
            '其他': Gender.OTHER
        }

        if gender in gender_mapping:
            return gender_mapping[gender]

        raise ValidationError(
            f"Invalid gender. Valid options: {', '.join(g.value for g in Gender)}"
        )


def validate_language(language: str) -> Language:
    """
    Validate language input and convert to Language enum.

    Args:
        language: Language string to validate

    Returns:
        Language enum value

    Raises:
        ValidationError: If language is invalid
    """
    if language is None:
        raise ValidationError("Language is required")

    # Sanitize input
    language = sanitize_text(language.lower().strip())

    if not language:
        raise ValidationError("Language cannot be empty")

    # Try to match with enum values
    try:
        return Language(language)
    except ValueError:
        # Check for common variations
        language_mapping = {
            'zh': Language.CHINESE,
            'chinese': Language.CHINESE,
            'cn': Language.CHINESE,
            '中文': Language.CHINESE,
            'en': Language.ENGLISH,
            'english': Language.ENGLISH,
            'eng': Language.ENGLISH
        }

        if language in language_mapping:
            return language_mapping[language]

        raise ValidationError(
            f"Invalid language. Valid options: {', '.join(l.value for l in Language)}"
        )


def validate_character_data(character_data: Dict[str, Any], character_index: int = 0) -> Dict[str, Any]:
    """
    Validate individual character configuration data.

    Args:
        character_data: Dictionary containing character configuration
        character_index: Index of the character for error messages

    Returns:
        Validated character data dictionary

    Raises:
        ValidationError: If character data is invalid
    """
    if not isinstance(character_data, dict):
        raise ValidationError(f"Character {character_index + 1} data must be a dictionary")

    validated = {}

    # Validate and extract name
    if 'name' not in character_data:
        raise ValidationError(f"Character {character_index + 1} name is required")

    validated['name'] = sanitize_text(character_data['name'])
    if not validated['name']:
        raise ValidationError(f"Character {character_index + 1} name cannot be empty")

    # Validate and extract gender
    if 'gender' not in character_data:
        raise ValidationError(f"Character {character_index + 1} gender is required")

    validated['gender'] = validate_gender(character_data['gender'])

    # Validate and extract background
    if 'background' not in character_data:
        raise ValidationError(f"Character {character_index + 1} background is required")

    validated['background'] = sanitize_text(character_data['background'])
    if not validated['background']:
        raise ValidationError(f"Character {character_index + 1} background cannot be empty")

    # Validate and extract personality
    if 'personality' not in character_data:
        raise ValidationError(f"Character {character_index + 1} personality is required")

    validated['personality'] = sanitize_text(character_data['personality'])
    if not validated['personality']:
        raise ValidationError(f"Character {character_index + 1} personality cannot be empty")

    # Validate and extract age (optional for backward compatibility)
    if 'age' in character_data and character_data['age']:
        validated['age'] = sanitize_text(character_data['age'])
    else:
        validated['age'] = None

    # Validate and extract style (optional for backward compatibility)
    if 'style' in character_data and character_data['style']:
        validated['style'] = sanitize_text(character_data['style'])
    else:
        validated['style'] = None

    # Validate optional language
    if 'language' in character_data:
        validated['language'] = validate_language(character_data['language'])
    else:
        validated['language'] = Language.CHINESE  # Default language

    return validated


def validate_podcast_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate complete podcast configuration input data.

    Args:
        data: Form data dictionary containing all podcast configuration

    Returns:
        Validated and sanitized podcast data dictionary

    Raises:
        ValidationError: If any input data is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Input data must be a dictionary")

    validated = {}

    # Validate and extract topic
    if 'topic' not in data:
        raise ValidationError("Topic is required")

    validated['topic'] = sanitize_text(data['topic'])
    if not validated['topic']:
        raise ValidationError("Topic cannot be empty")

    # Validate and extract participant count
    if 'participant_count' not in data and 'participants' not in data:
        raise ValidationError("Participant count is required")

    participant_count = data.get('participant_count', data.get('participants'))
    validated['participant_count'] = validate_character_count(participant_count)

    # Validate and extract conversation rounds
    if 'conversation_rounds' not in data and 'rounds' not in data:
        raise ValidationError("Conversation rounds is required")

    rounds = data.get('conversation_rounds', data.get('rounds'))
    validated['conversation_rounds'] = validate_conversation_rounds(rounds)

    # Validate character configurations
    characters = []

    # Try to extract characters from different possible formats
    character_data_list = None

    print(f"=== DEBUG VALIDATOR: Extracting character data ===")
    print(f"All data keys: {list(data.keys())}")

    # Format 1: characters field (list of character objects)
    if 'characters' in data:
        character_data_list = data['characters']
        print(f"Found 'characters' field with type: {type(character_data_list)}")
        if isinstance(character_data_list, list):
            print(f"Characters list length: {len(character_data_list)}")
            for i, char in enumerate(character_data_list):
                print(f"  Character {i}: {char}")
    # Format 2: character_* fields (character_0, character_1, etc.)
    else:
        character_data_list = []
        i = 0
        while f'character_{i}' in data:
            char_data = data[f'character_{i}']
            print(f"Found character_{i}: {char_data} (type: {type(char_data)})")
            character_data_list.append(char_data)
            i += 1
        print(f"Found {len(character_data_list)} character_* fields")

    if not character_data_list:
        print("ERROR: No character configurations found!")
        raise ValidationError("Character configurations are required")

    print(f"=== END DEBUG VALIDATOR ===")

    if len(character_data_list) != validated['participant_count']:
        raise ValidationError(
            f"Number of characters ({len(character_data_list)}) must match "
            f"participant count ({validated['participant_count']})"
        )

    # Validate each character
    for i, character_data in enumerate(character_data_list):
        validated_character = validate_character_data(character_data, i)

        # Create Character instance to leverage model validation
        character = Character(
            id=str(i),  # Use index as ID
            name=validated_character['name'],
            gender=validated_character['gender'],
            background=validated_character['background'],
            personality=validated_character['personality'],
            age=validated_character['age'],
            style=validated_character['style'],
            language=validated_character['language']
        )

        characters.append(character)

    validated['characters'] = characters

    return validated


def validate_file_url(url: str) -> bool:
    """
    Validate if a URL is safe for file operations.

    Args:
        url: URL to validate

    Returns:
        True if URL is safe, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        # Only allow specific schemes
        if parsed.scheme not in ['http', 'https', 'file']:
            return False

        # Reject potentially dangerous patterns
        dangerous_patterns = ['..', '~/', '\\']
        for pattern in dangerous_patterns:
            if pattern in url:
                return False

        return True

    except Exception:
        return False


def validate_audio_format(format_str: str) -> str:
    """
    Validate audio format string.

    Args:
        format_str: Audio format to validate

    Returns:
        Validated lowercase format string

    Raises:
        ValidationError: If format is invalid
    """
    if not format_str:
        return 'mp3'  # Default format

    format_str = sanitize_text(format_str.lower().strip())
    valid_formats = ['mp3', 'wav', 'ogg', 'm4a']

    if format_str not in valid_formats:
        raise ValidationError(
            f"Invalid audio format. Valid options: {', '.join(valid_formats)}"
        )

    return format_str


def validate_api_key_format(provider: str, api_key: str) -> bool:
    """
    Validate API key format for different AI providers using regex patterns.

    This function ensures API key format compliance and security by checking
    provider-specific patterns, length requirements, and character constraints.
    It validates against common API key formats while maintaining security standards.

    Args:
        provider: The AI provider name (e.g., 'deepseek', 'bigmodel')
        api_key: The API key to validate

    Returns:
        True if the API key format is valid for the specified provider

    Raises:
        ValidationError: If provider is unsupported or API key format is invalid

    Examples:
        >>> validate_api_key_format('deepseek', 'sk-1234567890abcdef1234567890abcdef')
        True
        >>> validate_api_key_format('bigmodel', '1234567890abcdef1234567890abcdef1234')
        True
        >>> validate_api_key_format('deepseek', 'invalid-key')
        ValidationError: Invalid API key format for DeepSeek
    """
    if not provider or not isinstance(provider, str):
        raise ValidationError("Provider is required and must be a string", field="provider")

    if not api_key or not isinstance(api_key, str):
        raise ValidationError("API key is required and must be a string", field="api_key")

    # Normalize provider name
    provider_key = provider.lower().strip()

    # Check if provider is supported
    if provider_key not in SUPPORTED_AI_PROVIDERS:
        supported_providers = ', '.join(SUPPORTED_AI_PROVIDERS.keys())
        raise ValidationError(
            f"Unsupported provider '{provider}'. Supported providers: {supported_providers}",
            field="provider"
        )

    # Get provider-specific validation rules
    provider_info = SUPPORTED_AI_PROVIDERS[provider_key]
    key_prefix = provider_info.get('key_prefix', '')
    min_length = provider_info.get('min_length', 20)
    provider_name = provider_info.get('name', provider.capitalize())

    # Sanitize and normalize API key
    api_key = api_key.strip()

    # Validate minimum length requirement
    if len(api_key) < min_length:
        raise ValidationError(
            f"API key must be at least {min_length} characters long for {provider_name}",
            field="api_key"
        )

    # Validate key prefix if required
    if key_prefix and not api_key.startswith(key_prefix):
        raise ValidationError(
            f"API key must start with '{key_prefix}' for {provider_name}",
            field="api_key"
        )

    # Provider-specific regex pattern validation
    validation_patterns = {
        'deepseek': {
            'pattern': r'^sk-[a-zA-Z0-9]{20,}$',
            'description': 'must start with "sk-" followed by alphanumeric characters'
        },
        'bigmodel': {
            'pattern': r'^[a-zA-Z0-9]{32,}$',
            'description': 'must be 32+ alphanumeric characters'
        }
    }

    # Get validation pattern for the provider
    if provider_key in validation_patterns:
        pattern_info = validation_patterns[provider_key]
        pattern = pattern_info['pattern']
        description = pattern_info['description']

        if not re.match(pattern, api_key):
            raise ValidationError(
                f"Invalid API key format for {provider_name}: {description}",
                field="api_key"
            )

    # Additional security validations
    # Check for common invalid patterns
    invalid_patterns = [
        r'^test.*$',           # Keys starting with "test"
        r'^demo.*$',           # Keys starting with "demo"
        r'^fake.*$',           # Keys starting with "fake"
        r'^[0]+$',             # All zeros
        r'^[a]+$',             # All same letter
        r'^.{1,5}$',           # Too short (additional check)
        r'(.)\1{10,}',        # Repeated characters (more than 10 times)
    ]

    for invalid_pattern in invalid_patterns:
        if re.match(invalid_pattern, api_key, re.IGNORECASE):
            raise ValidationError(
                f"API key contains invalid pattern for {provider_name}",
                field="api_key"
            )

    # Character set validation - ensure only valid characters
    valid_char_pattern = r'^[a-zA-Z0-9\-_]+$'
    if not re.match(valid_char_pattern, api_key):
        raise ValidationError(
            f"API key contains invalid characters for {provider_name}. "
            "Only alphanumeric characters, hyphens, and underscores are allowed",
            field="api_key"
        )

    # Entropy check - ensure sufficient complexity (basic)
    unique_chars = len(set(api_key))
    if unique_chars < len(api_key) * 0.3:  # At least 30% unique characters
        raise ValidationError(
            f"API key appears to have insufficient complexity for {provider_name}",
            field="api_key"
        )

    return True


def validate_provider_name(provider: str) -> str:
    """
    Validate and normalize provider name.

    Args:
        provider: The provider name to validate

    Returns:
        Normalized provider name in lowercase

    Raises:
        ValidationError: If provider is not supported
    """
    if not provider or not isinstance(provider, str):
        raise ValidationError("Provider is required and must be a string", field="provider")

    provider_key = provider.lower().strip()

    if provider_key not in SUPPORTED_AI_PROVIDERS:
        supported_providers = ', '.join(SUPPORTED_AI_PROVIDERS.keys())
        raise ValidationError(
            f"Unsupported provider '{provider}'. Supported providers: {supported_providers}",
            field="provider"
        )

    return provider_key


def get_api_key_validation_rules(provider: str) -> Dict[str, Any]:
    """
    Get validation rules for a specific API provider.

    Args:
        provider: The provider name

    Returns:
        Dictionary containing validation rules for the provider

    Raises:
        ValidationError: If provider is not supported
    """
    provider_key = validate_provider_name(provider)
    provider_info = SUPPORTED_AI_PROVIDERS[provider_key]

    return {
        'provider': provider_key,
        'name': provider_info.get('name', provider.capitalize()),
        'min_length': provider_info.get('min_length', 20),
        'key_prefix': provider_info.get('key_prefix', ''),
        'models': provider_info.get('models', []),
        'description': f"API key for {provider_info.get('name', provider.capitalize())}"
    }


# Utility function for creating validation error responses
def create_validation_error_response(error: ValidationError) -> Dict[str, Any]:
    """
    Create a standardized error response for validation failures.

    Args:
        error: ValidationError instance

    Returns:
        Dictionary with error information suitable for JSON response
    """
    response = {
        'success': False,
        'error': error.message,
        'error_type': 'validation_error'
    }

    if error.field:
        response['field'] = error.field

    return response


# Batch validation function for multiple fields
def validate_fields(fields: Dict[str, Any], rules: Dict[str, callable]) -> Dict[str, Any]:
    """
    Validate multiple fields using provided validation rules.

    Args:
        fields: Dictionary of field values to validate
        rules: Dictionary mapping field names to validation functions

    Returns:
        Dictionary with validated field values

    Raises:
        ValidationError: If any field validation fails
    """
    validated = {}

    for field_name, validator_func in rules.items():
        if field_name in fields:
            try:
                validated[field_name] = validator_func(fields[field_name])
            except ValidationError as e:
                # Add field name to error if not present
                if not e.field:
                    e.field = field_name
                raise
        else:
            raise ValidationError(f"Required field '{field_name}' is missing", field_name)

    return validated