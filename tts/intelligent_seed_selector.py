"""
Intelligent Seed Selector for ChatTTS

This module provides intelligent seed selection based on gender, age, and voice characteristics
using the seed_id.txt database. It selects the best seed with the highest rank_multi score
that matches the user's requirements.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SeedInfo:
    """Data class to hold seed information"""
    seed_id: str
    rank_long: float
    rank_multi: float
    rank_single: float
    score: float
    gender_distribution: Dict[str, float]
    age_distribution: Dict[str, float]
    features: List[Tuple[str, float]]

    def __str__(self):
        return (f"SeedInfo(seed={self.seed_id}, rank_multi={self.rank_multi}, "
                f"gender={list(self.gender_distribution.keys())}, "
                f"age={list(self.age_distribution.keys())}, "
                f"features={', '.join([f[0] for f in self.features[:3]])})")

class IntelligentSeedSelector:
    """
    Intelligent seed selector that chooses the best ChatTTS seed based on user requirements.
    """

    def __init__(self, seed_file_path: str = "seed_id.txt"):
        """
        Initialize the seed selector with seed database.

        Args:
            seed_file_path: Path to the seed_id.txt file
        """
        self.logger = logging.getLogger(__name__)
        self.seed_database: List[SeedInfo] = []
        self.load_seed_database(seed_file_path)

    def load_seed_database(self, seed_file_path: str):
        """Load and parse the seed database from seed_id.txt file."""
        try:
            seed_file = Path(seed_file_path)
            if not seed_file.exists():
                self.logger.warning(f"Seed file {seed_file_path} not found, using fallback seeds")
                self._create_fallback_database()
                return

            with open(seed_file, 'r', encoding='utf-8') as f:
                content = f.read()

            self._parse_seed_content(content)
            self.logger.info(f"Loaded {len(self.seed_database)} seeds from database")

        except Exception as e:
            self.logger.error(f"Failed to load seed database: {e}")
            self._create_fallback_database()

    def _parse_seed_content(self, content: str):
        """Parse the seed content from the file."""
        # Split by line and process in chunks
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        # Find all seed entries
        seed_entries = []
        current_entry = []

        for line in lines:
            if line.startswith('seed_') and current_entry:
                # Save previous entry
                seed_entries.append(current_entry)
                current_entry = [line]
            elif line or current_entry:
                current_entry.append(line)

        # Add last entry
        if current_entry:
            seed_entries.append(current_entry)

        # Process each seed entry
        for entry in seed_entries:
            try:
                if len(entry) < 8:
                    continue

                # Extract seed info
                seed_id = entry[0].replace('seed_', '')

                # Find numeric values (skip empty lines)
                values = []
                for line in entry[1:]:
                    if line and line.replace('.', '').isdigit():
                        values.append(float(line))
                    elif len(values) >= 4:  # Once we have 4 numeric values, start collecting text data
                        break

                if len(values) < 4:
                    self.logger.warning(f"Insufficient numeric data for seed {seed_id}")
                    continue

                rank_long, rank_multi, rank_single, score = values[:4]

                # Find text sections
                text_sections = []
                collecting_text = False
                current_text = []

                for line in entry[1:]:
                    if line.replace('.', '').isdigit():
                        collecting_text = False
                        if current_text:
                            text_sections.append(' '.join(current_text))
                            current_text = []
                    elif '%' in line or any(char in line for char in ['男', '女', '青年', '中年', '亲切', '温柔', '成熟']):
                        collecting_text = True
                        current_text.append(line)
                    elif collecting_text:
                        current_text.append(line)

                if current_text:
                    text_sections.append(' '.join(current_text))

                # Extract text data
                gender_info = text_sections[0] if len(text_sections) > 0 else ""
                age_info = text_sections[1] if len(text_sections) > 1 else ""
                feature_info = text_sections[2] if len(text_sections) > 2 else ""

                # Parse distributions
                gender_distribution = self._parse_distribution(gender_info)
                age_distribution = self._parse_distribution(age_info)
                features = self._parse_features(feature_info)

                seed_info = SeedInfo(
                    seed_id=seed_id,
                    rank_long=rank_long,
                    rank_multi=rank_multi,
                    rank_single=rank_single,
                    score=score,
                    gender_distribution=gender_distribution,
                    age_distribution=age_distribution,
                    features=features
                )

                self.seed_database.append(seed_info)
                self.logger.debug(f"Parsed seed {seed_id}: rank_multi={rank_multi}")

            except (ValueError, IndexError) as e:
                self.logger.warning(f"Failed to parse seed entry: {e}")
                continue

    def _parse_distribution(self, distribution_str: str) -> Dict[str, float]:
        """Parse gender or age distribution string into dictionary."""
        distribution = {}

        # Handle cases like "女 100.00%" or "男 61.49% 女 38.51%"
        parts = distribution_str.split()
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                key = parts[i]
                try:
                    value_str = parts[i+1].rstrip('%')
                    value = float(value_str) / 100.0
                    distribution[key] = value
                except ValueError:
                    continue

        return distribution

    def _parse_features(self, feature_str: str) -> List[Tuple[str, float]]:
        """Parse feature string into list of (feature, percentage) tuples."""
        features = []

        # Handle cases like "亲切 100.00%" or "成熟 27.08% 知性 26.71% 温柔 24.88%"
        parts = feature_str.split()
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                feature = parts[i]
                try:
                    percentage_str = parts[i+1].rstrip('%')
                    percentage = float(percentage_str) / 100.0
                    features.append((feature, percentage))
                except ValueError:
                    continue

        return features

    def _create_fallback_database(self):
        """Create a fallback seed database when file is not available."""
        self.logger.info("Creating fallback seed database")

        fallback_seeds = [
            SeedInfo("1283", 78.6, 87.16, 84.78, 0.32,
                     {"女": 1.0}, {"青年": 1.0}, [("亲切", 1.0)]),
            SeedInfo("2241", 60.78, 87.15, 86.47, 0.41,
                     {"女": 1.0}, {"青年": 0.73, "中年": 0.27},
                     [("成熟", 0.27), ("知性", 0.27), ("温柔", 0.25), ("亲切", 0.21)]),
            SeedInfo("614", 88.62, 87.13, 86.44, 0.4,
                     {"女": 1.0}, {"青年": 0.35, "中年": 0.65},
                     [("温柔", 0.35), ("东北", 0.33), ("成熟", 0.32)]),
            SeedInfo("731", 88.61, 87.13, 88.2, 0.35,
                     {"女": 1.0}, {"青年": 1.0}, [("成熟", 1.0)]),
            SeedInfo("579", 87.07, 87.12, 87.06, 0.41,
                     {"男": 1.0}, {"中年": 1.0}, [("浑厚", 1.0)]),
            SeedInfo("2550", 89.51, 87.06, 89.72, 0.31,
                     {"男": 1.0}, {"青年": 1.0}, [("时尚", 1.0)]),
        ]

        self.seed_database = fallback_seeds

    def select_best_seed(self,
                        gender: str = None,
                        age: str = None,
                        features: List[str] = None,
                        voice_preference: str = None) -> Optional[SeedInfo]:
        """
        Select the best seed based on user requirements.

        Args:
            gender: Preferred gender ('男', '女', or None)
            age: Preferred age ('青年', '中年', '老年', '少儿', or None)
            features: List of desired features (e.g., ['亲切', '温柔'])
            voice_preference: Voice preference description

        Returns:
            Best matching SeedInfo object or None if no match found
        """
        if not self.seed_database:
            self.logger.warning("No seed database available")
            return None

        # Filter seeds by gender preference
        candidate_seeds = self._filter_by_gender(self.seed_database, gender)

        # Filter by age preference
        candidate_seeds = self._filter_by_age(candidate_seeds, age)

        # Filter by features
        candidate_seeds = self._filter_by_features(candidate_seeds, features)

        # Filter by voice preference
        candidate_seeds = self._filter_by_voice_preference(candidate_seeds, voice_preference)

        if not candidate_seeds:
            self.logger.warning("No seeds match the criteria, returning best available")
            candidate_seeds = self.seed_database

        # Sort by rank_multi (highest first) and return the best
        best_seed = max(candidate_seeds, key=lambda x: x.rank_multi)

        self.logger.info(f"Selected seed {best_seed.seed_id} with rank_multi {best_seed.rank_multi}")
        return best_seed

    def _filter_by_gender(self, seeds: List[SeedInfo], gender: str) -> List[SeedInfo]:
        """Filter seeds by gender preference."""
        if not gender:
            return seeds

        gender_matches = []
        for seed in seeds:
            if gender in seed.gender_distribution and seed.gender_distribution[gender] > 0.3:
                gender_matches.append(seed)

        return gender_matches if gender_matches else seeds

    def _filter_by_age(self, seeds: List[SeedInfo], age: str) -> List[SeedInfo]:
        """Filter seeds by age preference."""
        if not age:
            return seeds

        age_matches = []
        for seed in seeds:
            if age in seed.age_distribution and seed.age_distribution[age] > 0.2:
                age_matches.append(seed)

        return age_matches if age_matches else seeds

    def _filter_by_features(self, seeds: List[SeedInfo], features: List[str]) -> List[SeedInfo]:
        """Filter seeds by feature preferences."""
        if not features:
            return seeds

        feature_matches = []
        for seed in seeds:
            seed_features = {f[0] for f in seed.features}
            feature_overlap = len(set(features) & seed_features)
            if feature_overlap > 0:
                feature_matches.append(seed)

        return feature_matches if feature_matches else seeds

    def _filter_by_voice_preference(self, seeds: List[SeedInfo], voice_preference: str) -> List[SeedInfo]:
        """Filter seeds by voice preference text."""
        if not voice_preference:
            return seeds

        # Map voice preferences to features
        preference_mapping = {
            '温柔': ['温柔', '亲切'],
            '成熟': ['成熟', '浑厚'],
            '年轻': ['青年', '时尚'],
            '专业': ['知性', '专业'],
            '亲切': ['亲切', '温柔'],
            '时尚': ['时尚', '年轻'],
            '浑厚': ['浑厚', '成熟'],
            '知性': ['知性', '成熟'],
            '东北': ['东北'],
            '译制腔': ['译制腔'],
            '普通': ['普通'],
        }

        matching_features = preference_mapping.get(voice_preference, [voice_preference])
        return self._filter_by_features(seeds, matching_features)

    def get_seed_recommendations(self,
                                gender: str = None,
                                age: str = None,
                                features: List[str] = None,
                                voice_preference: str = None,
                                top_n: int = 5) -> List[SeedInfo]:
        """
        Get top N seed recommendations based on criteria.

        Args:
            gender: Preferred gender
            age: Preferred age
            features: List of desired features
            voice_preference: Voice preference description
            top_n: Number of recommendations to return

        Returns:
            List of recommended SeedInfo objects sorted by rank_multi
        """
        if not self.seed_database:
            return []

        # Filter seeds based on criteria
        candidate_seeds = self._filter_by_gender(self.seed_database, gender)
        candidate_seeds = self._filter_by_age(candidate_seeds, age)
        candidate_seeds = self._filter_by_features(candidate_seeds, features)
        candidate_seeds = self._filter_by_voice_preference(candidate_seeds, voice_preference)

        if not candidate_seeds:
            candidate_seeds = self.seed_database

        # Sort by rank_multi and return top N
        return sorted(candidate_seeds, key=lambda x: x.rank_multi, reverse=True)[:top_n]

    def print_seed_table(self):
        """Print a formatted table of all available seeds."""
        print("\n" + "="*100)
        print("CHAT TTS 种子数据库 (按 rank_multi 排序)")
        print("="*100)
        print(f"{'种子ID':<8} {'Rank_Multi':<12} {'性别':<15} {'年龄':<15} {'主要特征':<20} {'评分':<8}")
        print("-"*100)

        # Sort by rank_multi
        sorted_seeds = sorted(self.seed_database, key=lambda x: x.rank_multi, reverse=True)

        for seed in sorted_seeds:
            # Get primary gender (highest percentage)
            primary_gender = max(seed.gender_distribution.items(), key=lambda x: x[1])[0]

            # Get primary age (highest percentage)
            primary_age = max(seed.age_distribution.items(), key=lambda x: x[1])[0]

            # Get top 3 features
            top_features = ', '.join([f[0] for f in seed.features[:3]])
            if len(top_features) > 18:
                top_features = top_features[:15] + "..."

            print(f"{seed.seed_id:<8} {seed.rank_multi:<12.2f} {primary_gender:<15} {primary_age:<15} {top_features:<20} {seed.score:<8.2f}")

        print("="*100)

    def get_gender_age_feature_mapping(self) -> Dict[str, Dict]:
        """
        Create a comprehensive mapping table for gender, age, and features.

        Returns:
            Dictionary with mappings for quick lookup
        """
        mapping = {
            'gender_mapping': {},
            'age_mapping': {},
            'feature_mapping': {}
        }

        # Build gender mapping
        for seed in self.seed_database:
            for gender, percentage in seed.gender_distribution.items():
                if gender not in mapping['gender_mapping']:
                    mapping['gender_mapping'][gender] = []

                if percentage > 0.5:  # Only include primary genders
                    mapping['gender_mapping'][gender].append({
                        'seed_id': seed.seed_id,
                        'rank_multi': seed.rank_multi,
                        'primary_age': max(seed.age_distribution.items(), key=lambda x: x[1])[0],
                        'primary_features': [f[0] for f in seed.features[:3]]
                    })

        # Sort each gender's seeds by rank_multi
        for gender in mapping['gender_mapping']:
            mapping['gender_mapping'][gender].sort(key=lambda x: x['rank_multi'], reverse=True)

        # Build age mapping
        for seed in self.seed_database:
            for age, percentage in seed.age_distribution.items():
                if age not in mapping['age_mapping']:
                    mapping['age_mapping'][age] = []

                if percentage > 0.3:  # Only include significant ages
                    mapping['age_mapping'][age].append({
                        'seed_id': seed.seed_id,
                        'rank_multi': seed.rank_multi,
                        'primary_gender': max(seed.gender_distribution.items(), key=lambda x: x[1])[0],
                        'primary_features': [f[0] for f in seed.features[:3]]
                    })

        # Sort each age's seeds by rank_multi
        for age in mapping['age_mapping']:
            mapping['age_mapping'][age].sort(key=lambda x: x['rank_multi'], reverse=True)

        # Build feature mapping
        for seed in self.seed_database:
            for feature, percentage in seed.features:
                if feature not in mapping['feature_mapping']:
                    mapping['feature_mapping'][feature] = []

                if percentage > 0.2:  # Only include significant features
                    mapping['feature_mapping'][feature].append({
                        'seed_id': seed.seed_id,
                        'rank_multi': seed.rank_multi,
                        'primary_gender': max(seed.gender_distribution.items(), key=lambda x: x[1])[0],
                        'primary_age': max(seed.age_distribution.items(), key=lambda x: x[1])[0]
                    })

        # Sort each feature's seeds by rank_multi
        for feature in mapping['feature_mapping']:
            mapping['feature_mapping'][feature].sort(key=lambda x: x['rank_multi'], reverse=True)

        return mapping

# Global seed selector instance
_seed_selector_instance = None

def get_seed_selector() -> IntelligentSeedSelector:
    """Get the global seed selector instance."""
    global _seed_selector_instance
    if _seed_selector_instance is None:
        _seed_selector_instance = IntelligentSeedSelector()
    return _seed_selector_instance

def select_best_seed(gender: str = None, age: str = None, features: List[str] = None,
                    voice_preference: str = None) -> Optional[str]:
    """
    Convenience function to select the best seed.

    Args:
        gender: Preferred gender ('男', '女')
        age: Preferred age ('青年', '中年', '老年', '少儿')
        features: List of desired features
        voice_preference: Voice preference description

    Returns:
        Best seed ID or None
    """
    selector = get_seed_selector()
    best_seed = selector.select_best_seed(gender, age, features, voice_preference)
    return best_seed.seed_id if best_seed else None

def create_seed_mapping_table():
    """Create and return a comprehensive seed mapping table."""
    selector = get_seed_selector()
    return selector.get_gender_age_feature_mapping()