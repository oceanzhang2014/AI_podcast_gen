#!/usr/bin/env python3
"""
Trace through the exact get_voice_preferences_for_frontend method step by step
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

def trace_frontend_processing():
    """Trace through the frontend processing step by step"""
    print("=== Trace Frontend Processing Step by Step ===\n")

    try:
        from tts.chattts_engine import ChatTTSEngine

        # Create the engine
        engine = ChatTTSEngine("debug_output")

        # Get the raw data
        voice_styles = engine.voice_preferences.get("声音偏好", {})
        gender_options = engine.voice_preferences.get("性别选项", {})
        age_options = engine.voice_preferences.get("年龄选项", {})
        seed_mapping = engine.voice_preferences.get("种子对照表", {})

        print(f"[STEP 1] Raw data loaded:")
        print(f"  Voice styles: {len(voice_styles)}")
        print(f"  Gender options: {len(gender_options)}")
        print(f"  Age options: {len(age_options)}")
        print(f"  Seed mapping: {len(seed_mapping)}")

        # Step 1: Initialize frontend_data structure
        frontend_data = {
            "声音偏好": {},
            "性别选项": gender_options,
            "年龄选项": age_options,
            "性别映射": gender_options,
            "年龄映射": age_options,
            "种子对照表": seed_mapping
        }

        # Step 2: Organize voice styles with descriptions
        for style_name, style_data in voice_styles.items():
            frontend_data["声音偏好"][style_name] = {
                "description": style_data.get("description", ""),
                "适用组合": []
            }

        print(f"\n[STEP 2] Initialized {len(frontend_data['声音偏好'])} voice styles")

        # Step 3: Process each seed
        print(f"\n[STEP 3] Processing seeds:")
        middle_aged_male_combos_created = 0

        for seed, seed_info in seed_mapping.items():
            gender = seed_info.get('gender')
            age = seed_info.get('age')
            style = seed_info.get('style')
            description = seed_info.get('description', '')

            print(f"  Processing seed {seed}: {gender} {age} {style}")

            if style in frontend_data["声音偏好"]:
                existing_combos = frontend_data["声音偏好"][style]["适用组合"]
                combo_exists = False

                for combo in existing_combos:
                    if combo["性别"] == gender and combo["年龄"] == age:
                        combo_exists = True
                        if "候选种子" not in combo:
                            combo["候选种子"] = []
                        combo["候选种子"].append({
                            "种子": seed,
                            "描述": description
                        })
                        print(f"    Added to existing combo")
                        break

                if not combo_exists:
                    new_combo = {
                        "性别": gender,
                        "性别显示": gender_options.get(gender, gender),
                        "年龄": age,
                        "年龄显示": age_options.get(age, age),
                        "候选种子": [{
                            "种子": seed,
                            "描述": description
                        }]
                    }
                    frontend_data["声音偏好"][style]["适用组合"].append(new_combo)
                    print(f"    Created new combo: {new_combo['年龄显示']} {new_combo['性别显示']}")

                    # Check if this is a middle-aged male combo
                    if age == '中年' and gender == 'male':
                        middle_aged_male_combos_created += 1
                        print(f"    *** MIDDLE-AGED MALE COMBO CREATED! ***")
            else:
                print(f"    ERROR: Style '{style}' not found in voice_styles")

        print(f"\n[RESULT] Created {middle_aged_male_combos_created} middle-aged male combos")

        # Step 4: Check all combinations in voice_styles
        print(f"\n[STEP 4] Checking all combinations in voice_styles:")
        total_combos = 0
        middle_aged_male_found = 0

        for style_name, style_data in frontend_data["声音偏好"].items():
            combos = style_data["适用组合"]
            total_combos += len(combos)
            print(f"  Style '{style_name}': {len(combos)} combos")

            for combo in combos:
                print(f"    {combo['年龄显示']} {combo['性别显示']} - {len(combo['候选种子'])} seeds")
                if combo['年龄'] == '中年' and combo['性别'] == 'male':
                    middle_aged_male_found += 1
                    print(f"      *** MIDDLE-AGED MALE FOUND! ***")

        print(f"\n[RESULT] Found {middle_aged_male_found} middle-aged male combos in voice_styles")
        print(f"[RESULT] Total combos in voice_styles: {total_combos}")

        # Step 5: Create flattened list
        print(f"\n[STEP 5] Creating flattened list:")
        all_combinations = []
        for style_name, style_data in frontend_data["声音偏好"].items():
            for combo in style_data["适用组合"]:
                all_combinations.append({
                    "年龄": combo["年龄"],
                    "年龄显示": combo["年龄显示"],
                    "风格": style_name,
                    "风格描述": style_data["description"],
                    "支持性别": [combo["性别显示"]],
                    "候选种子": combo["候选种子"]
                })

        print(f"  Flattened {len(all_combinations)} combinations")

        # Check middle-aged male in flattened list
        middle_aged_male_in_flat = 0
        for combo in all_combinations:
            if combo['年龄'] == '中年' and 'male' in combo['支持性别']:
                middle_aged_male_in_flat += 1
                print(f"    Found: {combo['年龄显示']} {combo['风格']} - {combo['支持性别']}")

        print(f"  Middle-aged male in flattened list: {middle_aged_male_in_flat}")

        # Step 6: Merge combinations
        print(f"\n[STEP 6] Merging combinations:")
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
            if combo["支持性别"][0] not in merged_combinations[key]["支持性别"]:
                merged_combinations[key]["支持性别"].append(combo["支持性别"][0])
            merged_combinations[key]["候选种子"].extend(combo["候选种子"])

        print(f"  Merged into {len(merged_combinations)} unique combinations")

        # Check middle-aged male in merged
        middle_aged_male_in_merged = 0
        for key, combo in merged_combinations.items():
            if combo['年龄'] == '中年' and 'male' in combo['支持性别']:
                middle_aged_male_in_merged += 1
                print(f"    Merged combo: {combo['年龄显示']} {combo['风格']} - {combo['支持性别']}")

        print(f"  Middle-aged male in merged: {middle_aged_male_in_merged}")

        # Final result
        frontend_data["所有组合"] = list(merged_combinations.values())
        print(f"\n[FINAL] Frontend data has {len(frontend_data['所有组合'])} combinations")

        # Count middle-aged male in final
        final_middle_aged_male = 0
        for combo in frontend_data["所有组合"]:
            if combo['年龄显示'] == '中年' and 'male' in combo['支持性别']:
                final_middle_aged_male += 1

        print(f"[FINAL] Middle-aged male combos in final result: {final_middle_aged_male}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_frontend_processing()