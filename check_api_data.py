#!/usr/bin/env python3
"""
Check API response data in detail
"""

import requests
import json

def check_api_data():
    """Check detailed API response data"""

    try:
        response = requests.get("http://127.0.0.1:5000/api/all-voice-combinations")

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                voice_data = data.get('data', {})

                print("=== API Data Analysis ===")
                print(f"Total keys in data: {len(voice_data)}")
                print(f"Keys: {list(voice_data.keys())}")

                # Check age options
                age_options = voice_data.get('年龄选项', {})
                print(f"\n年龄选项 type: {type(age_options)}")
                print(f"年龄选项 content: {age_options}")
                print(f"年龄选项 length: {len(age_options)}")

                # Check gender options
                gender_options = voice_data.get('性别选项', {})
                print(f"\n性别选项: {gender_options}")

                # Check all combinations
                all_combinations = voice_data.get('所有组合', [])
                print(f"\n所有组合 count: {len(all_combinations)}")

                if all_combinations:
                    print("Sample combinations:")
                    for i, combo in enumerate(all_combinations[:3]):
                        print(f"  {i+1}. {combo.get('年龄', 'N/A')} + {combo.get('风格', 'N/A')}")
                        print(f"     支持性别: {combo.get('支持性别', [])}")

                # Check voice preferences structure
                voice_preferences = voice_data.get('声音偏好', {})
                print(f"\n声音偏好 count: {len(voice_preferences)}")
                if voice_preferences:
                    print("声音偏好 categories:")
                    for style_name, style_data in list(voice_preferences.items())[:3]:
                        print(f"  - {style_name}: {type(style_data)}")
                        if isinstance(style_data, dict):
                            print(f"    Keys: {list(style_data.keys())}")

            else:
                print(f"API returned error: {data.get('error')}")
        else:
            print(f"HTTP error: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api_data()