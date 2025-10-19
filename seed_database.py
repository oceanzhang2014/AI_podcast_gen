"""
ChatTTS Seed Database - Direct seed selection based on gender, age, and features

This module provides a simplified seed database with the best seeds selected
from the seed_id.txt file, organized by rank_multi score.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class SeedData:
    """Data class for seed information"""
    seed_id: str
    rank_multi: float
    primary_gender: str
    primary_age: str
    features: List[str]
    description: str

# Best seeds from seed_id.txt organized by rank_multi (highest first)
SEED_DATABASE = {
    # Female voices
    "female_young_gentle": SeedData(
        seed_id="1283", rank_multi=87.16,
        primary_gender="女", primary_age="青年",
        features=["亲切"],
        description="青年女性亲切声音 (rank_multi: 87.16)"
    ),
    "female_young_mature": SeedData(
        seed_id="731", rank_multi=87.13,
        primary_gender="女", primary_age="青年",
        features=["成熟"],
        description="青年女性成熟声音 (rank_multi: 87.13)"
    ),
    "female_middle_age_gentle": SeedData(
        seed_id="2241", rank_multi=87.15,
        primary_gender="女", primary_age="中年",
        features=["成熟", "知性", "温柔", "亲切"],
        description="中年女性温柔知性声音 (rank_multi: 87.15)"
    ),
    "female_middle_age_mature": SeedData(
        seed_id="614", rank_multi=87.13,
        primary_gender="女", primary_age="中年",
        features=["温柔", "成熟"],
        description="中年女性温柔成熟声音 (rank_multi: 87.13)"
    ),
    "female_child_normal": SeedData(
        seed_id="1142", rank_multi=87.11,
        primary_gender="女", primary_age="青年",
        features=["普通"],
        description="女性普通声音 (rank_multi: 87.11)"
    ),
    "female_mixed_knowledgeable": SeedData(
        seed_id="1688", rank_multi=87.11,
        primary_gender="女", primary_age="青年",
        features=["译制腔", "成熟", "亲切"],
        description="女性知性声音 (rank_multi: 87.11)"
    ),

    # Male voices
    "male_middle_age_deep": SeedData(
        seed_id="579", rank_multi=87.12,
        primary_gender="男", primary_age="中年",
        features=["浑厚"],
        description="中年男性浑厚声音 (rank_multi: 87.12)"
    ),
    "male_young_fashionable": SeedData(
        seed_id="2550", rank_multi=87.06,
        primary_gender="男", primary_age="青年",
        features=["时尚"],
        description="青年男性时尚声音 (rank_multi: 87.06)"
    ),
    "mixed_gender_young": SeedData(
        seed_id="1075", rank_multi=87.12,
        primary_gender="男", primary_age="青年",
        features=["青年"],
        description="混合性别青年声音 - 男61.49% 女38.51% (rank_multi: 87.12)"
    ),
    "mixed_gender_professional": SeedData(
        seed_id="1005", rank_multi=87.11,
        primary_gender="女", primary_age="青年",
        features=["青年"],
        description="混合性别专业声音 - 女51.75% 男48.25% (rank_multi: 87.11)"
    ),
    "male_mixed_stylish": SeedData(
        seed_id="380", rank_multi=87.03,
        primary_gender="男", primary_age="青年",
        features=["时尚", "亲切"],
        description="混合性别时尚亲切声音 (rank_multi: 87.03)"
    ),
    "male_mixed_knowledgeable": SeedData(
        seed_id="839", rank_multi=87.02,
        primary_gender="男", primary_age="青年",
        features=["时尚", "知性"],
        description="混合性别知性声音 (rank_multi: 87.02)"
    ),
}

# Character seed cache for consistency
CHARACTER_SEED_CACHE: Dict[str, str] = {}

def get_best_seed_for_character(character_name: str,
                               gender: str = None,
                               age: str = None,
                               features: List[str] = None,
                               voice_preference: str = None) -> str:
    """
    Get the best seed for a character based on preferences.

    Args:
        character_name: Name of the character (for consistency)
        gender: Preferred gender ('男', '女')
        age: Preferred age ('青年', '中年', '老年', '少儿')
        features: List of desired features
        voice_preference: Voice preference description

    Returns:
        Best seed ID string
    """
    # Check if we already have a seed for this character
    if character_name and character_name in CHARACTER_SEED_CACHE:
        cached_seed = CHARACTER_SEED_CACHE[character_name]
        return cached_seed

    # Determine candidate seeds based on preferences
    candidate_seeds = []

    # Filter by gender - be more strict to avoid mixed-gender seeds
    if gender == "女":
        female_seeds = [s for s in SEED_DATABASE.values() if s.primary_gender == "女" and "混合性别" not in s.description]
        candidate_seeds.extend(female_seeds)
    elif gender == "男":
        male_seeds = [s for s in SEED_DATABASE.values() if s.primary_gender == "男" and "混合性别" not in s.description]
        candidate_seeds.extend(male_seeds)
    else:
        # No gender preference, include all
        candidate_seeds.extend(SEED_DATABASE.values())

    # Filter by age
    if age:
        age_seeds = [s for s in candidate_seeds if s.primary_age == age]
        if age_seeds:
            candidate_seeds = age_seeds

    # Filter by features
    if features:
        feature_seeds = []
        for seed in candidate_seeds:
            if any(feature in seed.features for feature in features):
                feature_seeds.append(seed)
        if feature_seeds:
            candidate_seeds = feature_seeds

    # Filter by voice preference
    if voice_preference:
        preference_mapping = {
            '温柔': ['gentle', 'soft'],
            '成熟': ['mature', 'deep'],
            '年轻': ['young', 'youthful'],
            '专业': ['professional', 'knowledgeable'],
            '亲切': ['gentle', 'friendly'],
            '时尚': ['fashionable', 'stylish'],
            '浑厚': ['deep', 'rich'],
            '知性': ['knowledgeable', 'intellectual'],
            '普通': ['normal', 'standard'],
        }

        preference_features = preference_mapping.get(voice_preference, [voice_preference])
        preference_seeds = []
        for seed in candidate_seeds:
            if any(pref in seed.features or pref in seed.description.lower()
                   for pref in preference_features):
                preference_seeds.append(seed)
        if preference_seeds:
            candidate_seeds = preference_seeds

    # If no candidates, use all seeds
    if not candidate_seeds:
        candidate_seeds = list(SEED_DATABASE.values())

    # Select best seed by rank_multi
    best_seed = max(candidate_seeds, key=lambda x: x.rank_multi)
    seed_id = best_seed.seed_id

    # Cache the seed for this character
    if character_name:
        CHARACTER_SEED_CACHE[character_name] = seed_id

    return seed_id

def get_seed_info(seed_id: str) -> Optional[SeedData]:
    """
    Get detailed information about a seed.

    Args:
        seed_id: The seed ID to look up

    Returns:
        SeedData object or None if not found
    """
    for seed in SEED_DATABASE.values():
        if seed.seed_id == seed_id:
            return seed
    return None

def print_seed_table():
    """Print a formatted table of available seeds."""
    print("\n" + "="*80)
    print("CHAT TTS 种子选择表 (按 rank_multi 评分排序)")
    print("="*80)
    print(f"{'种子ID':<8} {'Rank_Multi':<12} {'性别':<8} {'年龄':<8} {'主要特征':<20} {'描述'}")
    print("-"*80)

    # Sort by rank_multi
    sorted_seeds = sorted(SEED_DATABASE.values(), key=lambda x: x.rank_multi, reverse=True)

    for seed in sorted_seeds:
        features_str = ', '.join(seed.features[:3])
        if len(features_str) > 18:
            features_str = features_str[:15] + "..."
        description_short = seed.description[:30]
        if len(description_short) == 30:
            description_short += "..."

        print(f"{seed.seed_id:<8} {seed.rank_multi:<12.2f} {seed.primary_gender:<8} {seed.primary_age:<8} "
              f"{features_str:<20} {description_short}")

    print("="*80)

def get_recommendations(gender: str = None,
                      age: str = None,
                      features: List[str] = None,
                      voice_preference: str = None,
                      top_n: int = 3) -> List[SeedData]:
    """
    Get top N seed recommendations based on criteria.

    Args:
        gender: Preferred gender
        age: Preferred age
        features: List of desired features
        voice_preference: Voice preference description
        top_n: Number of recommendations to return

    Returns:
        List of recommended SeedData objects
    """
    # Determine candidate seeds based on preferences
    candidate_seeds = list(SEED_DATABASE.values())

    # Apply filters
    if gender == "女":
        candidate_seeds = [s for s in candidate_seeds if s.primary_gender == "女"]
    elif gender == "男":
        candidate_seeds = [s for s in candidate_seeds if s.primary_gender == "男"]

    if age:
        candidate_seeds = [s for s in candidate_seeds if s.primary_age == age]

    if features:
        candidate_seeds = [s for s in candidate_seeds if any(f in s.features for f in features)]

    if voice_preference:
        preference_keywords = voice_preference.lower()
        candidate_seeds = [s for s in candidate_seeds if any(keyword in s.description.lower()
                           for keyword in preference_keywords.split())]

    # Sort by rank_multi and return top N
    return sorted(candidate_seeds, key=lambda x: x.rank_multi, reverse=True)[:top_n]

# Predefined seed selections for common character types
PREDEFINED_SEEDS = {
    "female_host": "1283",      # 女主持人 - 亲切青年女声
    "male_host": "2550",        # 男主持人 - 时尚青年男声
    "female_professional": "2241",  # 女专家 - 知性中年女声
    "male_professional": "579",    # 男专家 - 浑厚中年男声
    "female_young": "731",       # 年轻女性 - 成熟青年女声
    "male_young": "1075",         # 年轻男性 - 青年混合声
    "female_mother": "614",      # 母亲声音 - 温柔中年女声
    "male_father": "579",        # 父亲声音 - 浑厚中年男声
}

def get_predefined_seed(character_type: str) -> Optional[str]:
    """
    Get a predefined seed for common character types.

    Args:
        character_type: Character type key

    Returns:
        Seed ID or None if not found
    """
    return PREDEFINED_SEEDS.get(character_type)

if __name__ == "__main__":
    # Test the seed database
    print_seed_table()

    # Test some selections
    print("\n测试种子选择:")
    print(f"温柔女声: {get_best_seed_for_character('温柔女声', gender='女', voice_preference='温柔')}")
    print(f"专业男声: {get_best_seed_for_character('专业男声', gender='男', voice_preference='专业')}")
    print(f"年轻女声: {get_best_seed_for_character('年轻女声', gender='女', age='青年')}")