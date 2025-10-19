#!/usr/bin/env python3
"""
Check available seed numbers in voice_preferences.json
"""
import json
import os

def check_available_seeds():
    """Check which seed numbers are already used"""
    print("=== Checking Available Seed Numbers ===\n")

    json_path = os.path.join(os.path.dirname(__file__), 'voice_preferences.json')

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            voice_preferences = json.load(f)

        seed_mapping = voice_preferences.get('种子对照表', {})

        used_seeds = []
        for seed_str in seed_mapping.keys():
            try:
                used_seeds.append(int(seed_str))
            except ValueError:
                used_seeds.append(seed_str)  # Non-numeric seed

        used_seeds.sort()
        print(f"Used seeds: {used_seeds}")

        # Find available numeric seeds
        max_used = max([s for s in used_seeds if isinstance(s, int)]) if used_seeds else 0
        print(f"Max used numeric seed: {max_used}")

        # Suggest next available seeds
        available_seeds = []
        for i in range(1, 10000):
            if i not in used_seeds:
                available_seeds.append(i)
                if len(available_seeds) >= 10:
                    break

        print(f"Available seeds: {available_seeds}")

        # Check if there's a pattern to current seeds
        print(f"\nCurrent seed patterns:")
        for seed in sorted(used_seeds):
            if isinstance(seed, int):
                info = seed_mapping[str(seed)]
                print(f"  {seed}: {info.get('gender')} {info.get('age')} {info.get('style')}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    check_available_seeds()