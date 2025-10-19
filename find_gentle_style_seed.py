#!/usr/bin/env python3
"""
Find which seed corresponds to 温柔风格
"""
import json
import os

def find_gentle_style_seed():
    """Find the seed for 温柔风格"""
    print("=== Finding 温柔风格 Seed ===\n")

    json_path = os.path.join(os.path.dirname(__file__), 'voice_preferences.json')

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            voice_preferences = json.load(f)

        seed_mapping = voice_preferences.get('种子对照表', {})

        gentle_seeds = []
        for seed, info in seed_mapping.items():
            if info.get('style') == '温柔风格':
                gentle_seeds.append((seed, info))

        print(f"Found {len(gentle_seeds)} seeds for 温柔风格:")
        for seed, info in gentle_seeds:
            print(f"  Seed {seed}: {info.get('gender')} {info.get('age')} - {info.get('description')}")

        # Check if there are any seeds with 温柔风格 and 中年 age
        middle_aged_gentle = []
        for seed, info in gentle_seeds:
            if info.get('age') == '中年':
                middle_aged_gentle.append((seed, info))

        print(f"\nMiddle-aged 温柔风格 seeds: {len(middle_aged_gentle)}")
        for seed, info in middle_aged_gentle:
            print(f"  Seed {seed}: {info}")

        # Check young 温柔风格 seeds too
        young_gentle = []
        for seed, info in gentle_seeds:
            if info.get('age') == '年轻':
                young_gentle.append((seed, info))

        print(f"\nYoung 温柔风格 seeds: {len(young_gentle)}")
        for seed, info in young_gentle:
            print(f"  Seed {seed}: {info}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    find_gentle_style_seed()