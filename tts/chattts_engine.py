"""
ChatTTS Engine - Based on testtts.py subprocess approach

Uses subprocess to call chattts command directly, which is the proven working approach.
"""

import os
import subprocess
import tempfile
import logging
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
import json
import hashlib

# Disable intelligent seed selector - only use testtts.py defined seeds
SEED_SELECTOR_AVAILABLE = False
get_best_seed_for_character = None
print("[INFO] Using only testtts.py defined voice seeds - intelligent seed selector disabled")


class ChatTTSEngine:
    """
    ChatTTS engine based on testtts.py subprocess approach.

    Uses subprocess to call chattts command directly with seed parameters.
    """

    def __init__(self, output_dir: str = "generated_audio"):
        """
        Initialize the ChatTTS engine.

        Args:
            output_dir: Directory to save generated audio files
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Load voice preferences from JSON file
        self.voice_preferences = self._load_voice_preferences()

        # Build voice seeds mapping from JSON
        self.voice_seeds = self._build_voice_seeds_mapping()

        # Character-to-seed mapping for consistency
        self.character_seed_cache: Dict[str, str] = {}

    def _load_voice_preferences(self) -> Dict:
        """Load voice preferences from JSON file"""
        try:
            json_path = Path(__file__).parent.parent / "voice_preferences.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
                self.logger.info(f"Loaded voice preferences from {json_path}")
                return preferences
            else:
                self.logger.warning(f"Voice preferences file not found: {json_path}")
                return self._get_fallback_preferences()
        except Exception as e:
            self.logger.error(f"Failed to load voice preferences: {e}")
            return self._get_fallback_preferences()

    def _get_fallback_preferences(self) -> Dict:
        """Get fallback voice preferences based on testtts.py"""
        return {
            "声音偏好": {
                "文学风格": {
                    "description": "知性文雅，适合朗读文学作品",
                    "male": {
                        "年轻": {"seed": 111, "description": "年轻男性 - 文学气质"}
                    }
                },
                "温柔风格": {
                    "description": "温和柔软，亲切自然",
                    "male": {
                        "年轻": {"seed": 333, "description": "年轻男性 - 温柔体贴"}
                    },
                    "female": {
                        "年轻": {"seed": 2, "description": "年轻女性 - 情感丰富温柔"}
                    }
                },
                "专业风格": {
                    "description": "专业稳重，适合正式场合",
                    "male": {
                        "中年": {"seed": 666, "description": "中年男性 - 白领专业"}
                    },
                    "female": {
                        "中年": {"seed": 1111, "description": "中年女性 - 专业清晰"}
                    }
                },
                "情感风格": {
                    "description": "情感丰富，表现力强",
                    "female": {
                        "年轻": {"seed": 2, "description": "年轻女性 - 情感丰富"}
                    }
                },
                "深情风格": {
                    "description": "深情动人，温暖感人",
                    "female": {
                        "中年": {"seed": 4, "description": "中年女性 - 深情动人"}
                    }
                },
                "平静风格": {
                    "description": "平静宁静，安详舒适",
                    "female": {
                        "中年": {"seed": 3333, "description": "中年女性 - 平静宁静"}
                    }
                }
            }
        }

    def _build_voice_seeds_mapping(self) -> Dict[str, Dict[str, str]]:
        """Build voice seeds mapping from JSON preferences"""
        voice_seeds = {
            'male': {},
            'female': {}
        }

        try:
            voice_preferences = self.voice_preferences.get("声音偏好", {})

            for style_name, style_data in voice_preferences.items():
                for gender, age_data in style_data.items():
                    if gender in ['male', 'female']:
                        for age, config in age_data.items():
                            # Create mapping keys for different age descriptions
                            age_key = age
                            if age_key == '年轻':
                                age_key = 'young'
                            elif age_key == '中年':
                                age_key = 'middle-aged'
                            elif age_key == '其他':
                                age_key = 'mature'

                            # Store seed mapping
                            seed = str(config['seed'])
                            voice_seeds[gender][age_key] = seed

                            # Also store style-based mappings
                            style_key = style_name.replace('风格', '').lower()
                            voice_seeds[gender][style_key] = seed

                            self.logger.debug(f"Added mapping: {gender} {age_key}/{style_key} -> seed {seed}")

        except Exception as e:
            self.logger.error(f"Error building voice seeds mapping: {e}")

        return voice_seeds

    def get_voice_preferences_for_frontend(self) -> Dict:
        """Get voice preferences organized by style for frontend character selection"""
        try:
            # Get basic options from JSON
            voice_styles = self.voice_preferences.get("声音偏好", {})
            gender_options = self.voice_preferences.get("性别选项", {})
            age_options = self.voice_preferences.get("年龄选项", {})
            seed_mapping = self.voice_preferences.get("种子对照表", {})

            # Prepare frontend data structure
            frontend_data = {
                "声音偏好": {},
                "性别选项": gender_options,
                "年龄选项": age_options,
                "性别映射": gender_options,
                "年龄映射": age_options,
                "种子对照表": seed_mapping
            }

            # Organize voice styles with descriptions
            for style_name, style_data in voice_styles.items():
                frontend_data["声音偏好"][style_name] = {
                    "description": style_data.get("description", ""),
                    "适用组合": []  # Valid gender+age combinations for this style
                }

            # For each style, find valid gender+age combinations from seed mapping
            for seed, seed_info in seed_mapping.items():
                gender = seed_info.get('gender')
                age = seed_info.get('age')
                style = seed_info.get('style')
                description = seed_info.get('description', '')

                if style in frontend_data["声音偏好"]:
                    # Check if this gender+age combination is already added
                    existing_combos = frontend_data["声音偏好"][style]["适用组合"]
                    combo_exists = False

                    for combo in existing_combos:
                        if combo["性别"] == gender and combo["年龄"] == age:
                            combo_exists = True
                            # Add seed to existing combo
                            if "候选种子" not in combo:
                                combo["候选种子"] = []
                            combo["候选种子"].append({
                                "种子": seed,
                                "描述": description
                            })
                            break

                    if not combo_exists:
                        # Add new combination
                        frontend_data["声音偏好"][style]["适用组合"].append({
                            "性别": gender,
                            "性别显示": gender_options.get(gender, gender),
                            "年龄": age,
                            "年龄显示": age_options.get(age, age),
                            "候选种子": [{
                                "种子": seed,
                                "描述": description
                            }]
                        })

            # Sort candidates within each combination
            for style_name in frontend_data["声音偏好"]:
                combos = frontend_data["声音偏好"][style_name]["适用组合"]
                for combo in combos:
                    combo["候选种子"].sort(key=lambda x: int(x["种子"]))
                    combo["候选数量"] = len(combo["候选种子"])

            # Create flattened list of all combinations for frontend filtering
            all_combinations = []
            for style_name, style_data in frontend_data["声音偏好"].items():
                for combo in style_data["适用组合"]:
                    all_combinations.append({
                        "年龄": combo["年龄"],
                        "年龄显示": combo["年龄显示"],
                        "风格": style_name,
                        "风格描述": style_data["description"],
                        "支持性别": [combo["性别显示"], combo["性别"]],
                        "候选种子": combo["候选种子"]
                    })

            # Merge combinations with same age+style but different genders
            merged_combinations = {}
            for combo in all_combinations:
                key = f"{combo['年龄']}_{combo['风格']}"
                if key not in merged_combinations:
                    merged_combinations[key] = {
                        "年龄": combo["年龄"],
                        "年龄显示": combo["年龄显示"],
                        "风格": combo["风格"],
                        "风格描述": combo["风格描述"],
                        "支持性别": [],
                        "候选种子": []
                    }

                # Merge genders and seeds
                for gender in combo["支持性别"]:
                    if gender not in merged_combinations[key]["支持性别"]:
                        merged_combinations[key]["支持性别"].append(gender)
                merged_combinations[key]["候选种子"].extend(combo["候选种子"])

            # Remove duplicates and sort
            frontend_data["所有组合"] = list(merged_combinations.values())
            for combo in frontend_data["所有组合"]:
                combo["支持性别"].sort()
                # Remove duplicate seeds and sort
                seen_seeds = set()
                unique_seeds = []
                for seed in combo["候选种子"]:
                    if seed["种子"] not in seen_seeds:
                        seen_seeds.add(seed["种子"])
                        unique_seeds.append(seed)
                combo["候选种子"] = sorted(unique_seeds, key=lambda x: int(x["种子"]))

            # Sort all combinations by age then style
            frontend_data["所有组合"].sort(key=lambda x: (x["年龄"], x["风格"]))

            # Add summary statistics
            total_styles = len(voice_styles)
            total_seeds = len(seed_mapping)
            total_combinations = sum(len(style_data["适用组合"]) for style_data in frontend_data["声音偏好"].values())

            frontend_data["统计信息"] = {
                "总风格数": total_styles,
                "总种子数": total_seeds,
                "总组合数": total_combinations,
                "所有组合数": len(frontend_data["所有组合"])
            }

            return frontend_data

        except Exception as e:
            self.logger.error(f"Error formatting voice preferences for frontend: {e}")
            return {}

    def get_age_style_combinations(self, gender: str) -> list:
        """Get all available age+style combinations for a specific gender"""
        try:
            seed_mapping = self.voice_preferences.get("种子对照表", {})
            combinations = {}

            for seed, seed_info in seed_mapping.items():
                if seed_info.get('gender') != gender:
                    continue

                age = seed_info.get('age')
                style = seed_info.get('style')
                description = seed_info.get('description', '')

                combination_key = f"{age}+{style}"
                if combination_key not in combinations:
                    combinations[combination_key] = {
                        "年龄": age,
                        "风格": style,
                        "候选种子": [],
                        "描述": []
                    }

                combinations[combination_key]["候选种子"].append(seed)
                combinations[combination_key]["描述"].append(description)

            # Convert to list and sort
            result = list(combinations.values())
            result.sort(key=lambda x: (x['年龄'], x['风格']))

            return result

        except Exception as e:
            self.logger.error(f"Error getting age+style combinations: {e}")
            return []

    def _get_character_seed(self, character_name: str, gender: str = None, personality: str = None, age: str = None, style: str = None) -> str:
        """
        Get a consistent seed for a character using JSON voice preferences.

        Args:
            character_name: Name of the character
            gender: Character gender (optional)
            personality: Character personality or voice style (optional)
            age: Character age (optional)
            style: Character voice style (optional)

        Returns:
            Seed string for ChatTTS from JSON-defined preferences
        """
        # Use provided age and style, or extract from personality, or use defaults
        if age is None:
            age = "中年"  # Default age
        if style is None:
            # Map personality to appropriate voice style
            style = self._map_personality_to_style(personality) or "专业风格"

        # Check cache first for character consistency (use more specific cache key)
        cache_key = f"{character_name}_{gender}_{age}_{style}"
        if cache_key in self.character_seed_cache:
            seed = self.character_seed_cache[cache_key]
            self.logger.info(f"Using cached seed '{seed}' for character '{character_name}' (gender: {gender}, age: {age}, style: {style})")
            return seed

        # Try to find seed from JSON voice preferences using the correct parameters
        seed = self._find_seed_from_preferences(character_name, gender, age, style)

        # Cache the seed for this character configuration
        self.character_seed_cache[cache_key] = seed

        return seed

    def _map_personality_to_style(self, personality: str) -> str:
        """
        Map frontend personality options to voice preference styles.

        Args:
            personality: Frontend personality (professional, casual, energetic, calm)

        Returns:
            Corresponding voice style from voice preferences JSON
        """
        if not personality:
            return None

        # Map personality to voice style
        personality_mapping = {
            'professional': '专业风格',
            'casual': '温柔风格',
            'energetic': '情感风格',
            'calm': '平静风格'
        }

        # Also support direct style names in Chinese
        if personality in ['专业风格', '温柔风格', '情感风格', '平静风格', '文学风格', '港式风格', '深沉风格', '清澈风格', '深情风格']:
            return personality

        return personality_mapping.get(personality.lower())

    def _find_seed_from_preferences(self, character_name: str, gender: str, age: str, style: str) -> str:
        """Find seed from JSON voice preferences using exact gender+age+style matching with random selection"""
        import random

        try:
            # Use the new method to get exact matches
            matching_candidates = self.get_candidates_by_preference(gender, age, style)

            if matching_candidates:
                # Random selection from matching candidates
                selected = random.choice(matching_candidates)
                seed = selected['seed']
                description = selected['description']

                self.logger.info(f"Found {len(matching_candidates)} matching candidates for {character_name} "
                               f"(gender: {gender}, age: {age}, style: {style}), "
                               f"randomly selected seed '{seed}': {description}")
                return seed
            else:
                self.logger.warning(f"No exact match found for {character_name} "
                                  f"(gender: {gender}, age: {age}, style: {style})")

                # No exact match, return fallback
                self.logger.info(f"No matching candidate found for {character_name} - using fallback")
                return self._get_fallback_seed(gender, character_name)

        except Exception as e:
            self.logger.error(f"Error finding seed from preferences: {e}")
            return self._get_fallback_seed(gender, character_name)

    def _get_fallback_seed(self, gender: str, character_name: str) -> str:
        """Get fallback seed when no exact match is found"""
        try:
            # Try to find best match with available options
            voice_styles = self.voice_preferences.get("声音偏好", {})
            seed_mapping = self.voice_preferences.get("种子对照表", {})

            # Try to find any combination with matching gender
            for seed, seed_info in seed_mapping.items():
                if seed_info.get('gender') == gender:
                    self.logger.info(f"Using fallback seed '{seed}' for {character_name} (gender: {gender})")
                    return seed

            # Ultimate fallback: use default seeds
            default_seeds = {
                'female': '1111',  # 清澈风格
                'male': '666'      # 专业风格
            }

            fallback_seed = default_seeds.get(gender.lower() if gender else 'female', '1111')
            self.logger.info(f"Using ultimate fallback seed '{fallback_seed}' for character '{character_name}'")
            return fallback_seed

        except Exception as e:
            self.logger.error(f"Error getting fallback seed: {e}")
            return '1111'  # Final fallback

    def _parse_personality(self, personality: str) -> tuple:
        """Parse personality string to extract age and style"""
        if not personality:
            return None, None

        # Split personality by spaces and try to identify age and style
        parts = personality.split()
        age = None
        style = None

        # Define possible age values
        age_values = ['年轻', '中年', '其他']

        for part in parts:
            # Check if this part is an age
            if part in age_values:
                age = part
            else:
                # Treat everything else as style (may contain multiple words)
                if style:
                    style += " " + part
                else:
                    style = part

        # Clean up style name (remove "风格" suffix if present)
        if style and not style.endswith('风格'):
            style += '风格'

        return age, style

    def get_matching_seeds(self, gender: str, age: str, style: str) -> list:
        """Get all seeds that match the exact gender + age + style combination"""
        try:
            seed_mapping = self.voice_preferences.get("种子对照表", {})
            matching_seeds = []

            for seed, seed_info in seed_mapping.items():
                if (seed_info.get('gender') == gender and
                    seed_info.get('age') == age and
                    seed_info.get('style') == style):
                    matching_seeds.append({
                        'seed': seed,
                        'description': seed_info.get('description', ''),
                        'gender': seed_info.get('gender'),
                        'age': seed_info.get('age'),
                        'style': seed_info.get('style')
                    })

            return matching_seeds

        except Exception as e:
            self.logger.error(f"Error getting matching seeds: {e}")
            return []

    def get_voice_candidates_by_gender_age_style(self, gender: str = None, age: str = None, style: str = None) -> list:
        """
        Get voice candidates filtered by gender, age, and style preferences.
        This is the main method for frontend to get candidate voices.
        """
        try:
            seed_mapping = self.voice_preferences.get("种子对照表", {})
            candidates = []

            for seed, seed_info in seed_mapping.items():
                # Filter by gender (required)
                if gender and seed_info.get('gender') != gender:
                    continue

                # Filter by age (if specified)
                if age and seed_info.get('age') != age:
                    continue

                # Filter by style (if specified)
                if style and seed_info.get('style') != style:
                    continue

                candidates.append({
                    'seed': seed,
                    'description': seed_info.get('description', ''),
                    'gender': seed_info.get('gender'),
                    'age': seed_info.get('age'),
                    'style': seed_info.get('style')
                })

            return candidates

        except Exception as e:
            self.logger.error(f"Error getting voice candidates: {e}")
            return []

    def get_candidates_by_preference(self, gender: str, age: str, style: str) -> list:
        """
        Get voice candidates by gender, age, and style preference combination.
        This is the main matching method for frontend character selection.
        """
        try:
            seed_mapping = self.voice_preferences.get("种子对照表", {})
            candidates = []

            for seed, seed_info in seed_mapping.items():
                # Exact match all three criteria
                if (seed_info.get('gender') == gender and
                    seed_info.get('age') == age and
                    seed_info.get('style') == style):
                    candidates.append({
                        'seed': seed,
                        'description': seed_info.get('description', ''),
                        'gender': seed_info.get('gender'),
                        'age': seed_info.get('age'),
                        'style': seed_info.get('style')
                    })

            return candidates

        except Exception as e:
            self.logger.error(f"Error getting candidates by preference: {e}")
            return []

    def get_available_voice_options(self, gender: str = None) -> List[Dict]:
        """Get available voice options filtered by gender"""
        try:
            voice_preferences = self.voice_preferences.get("声音偏好", {})
            options = []

            for style_name, style_data in voice_preferences.items():
                style_info = {
                    "风格": style_name,
                    "描述": style_data.get("description", ""),
                    "选项": []
                }

                genders_to_check = [gender] if gender else ['male', 'female']

                for check_gender in genders_to_check:
                    if check_gender in style_data:
                        for age, config in style_data[check_gender].items():
                            option = {
                                "性别": check_gender,
                                "年龄": age,
                                "种子": config['seed'],
                                "完整描述": config['description']
                            }
                            style_info["选项"].append(option)

                if style_info["选项"]:  # Only add if there are options
                    options.append(style_info)

            return options

        except Exception as e:
            self.logger.error(f"Error getting available voice options: {e}")
            return []

    def _find_best_matching_seed(self, gender: str, personality: str, character_name: str) -> str:
        """
        Find the best matching seed from testtts.py defined seeds when no exact match.

        Args:
            gender: Gender ('female' or 'male')
            personality: Personality description
            character_name: Character name for logging

        Returns:
            Best matching seed string
        """
        # Define personality keyword mappings to testtts.py seeds
        personality_mappings = {
            'female': {
                # Young female (seed: 2 - emotionally rich)
                'young': '2', 'emotionally': '2', 'emotional': '2', 'rich': '2',
                'lively': '2', 'energetic': '2', 'casual': '2',

                # Middle-aged female (seed: 4 - deeply emotional)
                'middle-aged': '4', 'deeply': '4', 'emotional': '4', 'deep': '4',
                'mature': '4', 'passionate': '4',

                # Clear and pure (seed: 1111)
                'clear': '1111', 'pure': '1111', 'clean': '1111', 'professional': '1111',
                'neutral': '1111', 'calm': '1111', 'serene': '1111',

                # Calm and serene (seed: 3333)
                'serene': '3333', 'peaceful': '3333', 'gentle': '3333', 'soft': '3333'
            },
            'male': {
                # Young male (seed: 111 - literary, seed: 333 - gentle)
                'young': '111', 'literary': '111', 'academic': '111', 'intellectual': '111',
                'gentle': '333', 'soft': '333', 'kind': '333',

                # Middle-aged male (seed: 666 - white-collar, seed: 7777 - hong kong-style)
                'middle-aged': '666', 'professional': '666', 'white-collar': '666',
                'business': '666', 'formal': '666', 'mature': '7777',

                # Hong Kong style (seed: 7777)
                'hong': '7777', 'kong': '7777', 'style': '7777', 'accent': '7777',

                # Deep and resonant (seed: 9999)
                'deep': '9999', 'resonant': '9999', 'authoritative': '9999',
                'powerful': '9999', 'strong': '9999'
            }
        }

        # Search for keyword matches
        personality_lower = personality.lower()
        gender_mappings = personality_mappings.get(gender, {})

        for keyword, seed in gender_mappings.items():
            if keyword in personality_lower:
                self.logger.info(f"Found keyword match '{keyword}' -> seed '{seed}' for character '{character_name}'")
                return seed

        # No keyword match found, use gender default
        default_seeds = {
            'female': '1111',  # Clear and pure
            'male': '666'      # White-collar
        }
        default_seed = default_seeds.get(gender, '1111')

        self.logger.info(f"No keyword match found for '{personality}', using default seed '{default_seed}' for character '{character_name}'")
        return default_seed

    def generate_audio(self, text: str, gender: str = None, personality: str = None,
                      output_file: Optional[str] = None, character_name: str = None,
                      age: str = None, style: str = None) -> Optional[str]:
        """
        Generate audio using ChatTTS subprocess call with consistent voice for characters.

        Args:
            text: Text to convert to speech
            gender: Character gender (optional)
            personality: Character personality (optional)
            output_file: Optional custom output file path
            character_name: Character name for voice consistency (optional)

        Returns:
            Path to generated audio file, or None if failed
        """
        try:
            # Preprocess text to avoid issues with spaces and special characters
            # Remove spaces and problematic punctuation like in testtts.py fix
            processed_text = text.strip()
            processed_text = processed_text.replace(' ', '')  # Remove spaces
            processed_text = processed_text.replace('.', '')  # Remove periods
            processed_text = processed_text.replace('!', '')  # Remove exclamation marks
            processed_text = processed_text.replace('?', '')  # Remove question marks
            processed_text = processed_text.replace(',', '')  # Remove commas
            processed_text = processed_text.replace('。', '')  # Remove Chinese periods
            processed_text = processed_text.replace('！', '')  # Remove Chinese exclamation marks
            processed_text = processed_text.replace('？', '')  # Remove Chinese question marks
            processed_text = processed_text.replace('，', '')  # Remove Chinese commas

            if not processed_text:
                self.logger.warning("Text is empty after preprocessing")
                return None

            # Get seed for voice consistency
            seed = self._get_character_seed(character_name or "unknown", gender, personality, age, style)

            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"chattts_{timestamp}.wav"

            output_path = self.output_dir / output_file

            self.logger.info(f"Generating ChatTTS audio via subprocess: {processed_text[:50]}... (seed: {seed}, character: {character_name})")

            # Build chattts command like in testtts.py
            # Use double quotes to avoid shell parsing issues
            command = f'chattts -s {seed} "{processed_text}"'

            # Run the chattts command using subprocess with better encoding handling
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',  # Ignore encoding errors like in testtts.py fix
                cwd=str(self.output_dir)  # Run in output directory
            )

            # Check if the default tts.wav file was created
            default_wav_path = self.output_dir / "tts.wav"
            if default_wav_path.exists():
                # Move the generated file to our desired output path
                import shutil
                shutil.move(str(default_wav_path), str(output_path))

                # Check if file was created successfully
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    self.logger.info(f"ChatTTS subprocess generation successful: {output_path} ({file_size} bytes)")
                    return str(output_path)
                else:
                    self.logger.error(f"Failed to move tts.wav to: {output_path}")
                    return None
            else:
                self.logger.error("ChatTTS subprocess did not generate tts.wav file")
                if result.stderr:
                    self.logger.error(f"Subprocess stderr: {result.stderr}")
                return None

        except subprocess.CalledProcessError as e:
            self.logger.error(f"ChatTTS subprocess failed with return code {e.returncode}")
            if e.stdout:
                self.logger.error(f"Subprocess stdout: {e.stdout}")
            if e.stderr:
                self.logger.error(f"Subprocess stderr: {e.stderr}")
            return None
        except Exception as e:
            self.logger.error(f"ChatTTS generation error: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def cleanup_temp_files(self, temp_files=None):
        """Clean up temporary files (interface compatibility)."""
        if temp_files:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {e}")

    def close(self):
        """Clean up resources."""
        self.logger.info("ChatTTS engine closed")


def create_chatts_engine(output_dir: str = "generated_audio") -> ChatTTSEngine:
    """
    Create a ChatTTS engine instance.

    Args:
        output_dir: Directory to save generated audio files

    Returns:
        ChatTTSEngine instance
    """
    return ChatTTSEngine(output_dir)