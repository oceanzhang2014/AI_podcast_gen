#!/usr/bin/env python3
"""
Voice Characteristic Verification Criteria

This module defines the criteria and methods for verifying that generated audio
matches the expected voice characteristics from the seed database.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

class VoiceCharacteristic(Enum):
    """Voice characteristics to evaluate"""
    GENDER = "gender"
    AGE = "age"
    PITCH = "pitch"
    SPEECH_RATE = "speech_rate"
    EMOTION = "emotion"
    TIMBRE = "timbre"
    ARTICULATION = "articulation"

@dataclass
class VerificationCriteria:
    """Criteria for verifying voice characteristics"""
    characteristic: VoiceCharacteristic
    expected_value: str
    description: str
    evaluation_method: str
    weight: float  # Importance weight for overall scoring

class VoiceVerificationSystem:
    """System for verifying voice characteristics against seed expectations"""

    def __init__(self):
        self.criteria_database = self._build_criteria_database()
        self.evaluation_questions = self._build_evaluation_questions()

    def _build_criteria_database(self) -> Dict[str, List[VerificationCriteria]]:
        """Build verification criteria for each seed feature"""
        criteria = {
            # Gender-based criteria
            "女": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.GENDER,
                    expected_value="女性",
                    description="声音应该表现为女性特征",
                    evaluation_method="听音辨性别 - 基频较高，音色较细",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.PITCH,
                    expected_value="较高",
                    description="基频应该在180-250Hz范围内",
                    evaluation_method="基频分析或主观听感",
                    weight=0.3
                ),
            ],
            "男": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.GENDER,
                    expected_value="男性",
                    description="声音应该表现为男性特征",
                    evaluation_method="听音辨性别 - 基频较低，音色较粗",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.PITCH,
                    expected_value="较低",
                    description="基频应该在100-150Hz范围内",
                    evaluation_method="基频分析或主观听感",
                    weight=0.3
                ),
            ],

            # Age-based criteria
            "青年": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.AGE,
                    expected_value="青年",
                    description="声音应该体现青年人的活力和清晰度",
                    evaluation_method="听感评估 - 发音清晰，语速适中偏快",
                    weight=0.3
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.SPEECH_RATE,
                    expected_value="4-5字/秒",
                    description="语速应该适中偏快，体现青年活力",
                    evaluation_method="计时分析或主观听感",
                    weight=0.2
                ),
            ],
            "中年": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.AGE,
                    expected_value="中年",
                    description="声音应该体现中年人的沉稳和经验",
                    evaluation_method="听感评估 - 语速稳定，音色沉稳",
                    weight=0.3
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.SPEECH_RATE,
                    expected_value="3-4字/秒",
                    description="语速应该适中，体现稳重",
                    evaluation_method="计时分析或主观听感",
                    weight=0.2
                ),
            ],
            "少儿": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.AGE,
                    expected_value="少儿",
                    description="声音应该体现儿童的稚嫩和活泼",
                    evaluation_method="听感评估 - 音调较高，发音较嫩",
                    weight=0.3
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.PITCH,
                    expected_value="很高",
                    description="基频应该明显高于成人",
                    evaluation_method="基频分析或主观听感",
                    weight=0.3
                ),
            ],

            # Feature-based criteria
            "亲切": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.EMOTION,
                    expected_value="温和友好",
                    description="声音应该传达亲切和温暖的感觉",
                    evaluation_method="情感分析 - 语调温和，带有微笑感",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.TIMBRE,
                    expected_value="温暖",
                    description="音色应该温暖柔和",
                    evaluation_method="音色分析或主观听感",
                    weight=0.3
                ),
            ],
            "成熟": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.AGE,
                    expected_value="成熟稳重",
                    description="声音应该体现成熟和稳重",
                    evaluation_method="听感评估 - 语调平稳，不急不躁",
                    weight=0.3
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.EMOTION,
                    expected_value="稳重",
                    description="情感表达应该稳重内敛",
                    evaluation_method="情感分析 - 情感起伏适中",
                    weight=0.3
                ),
            ],
            "温柔": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.EMOTION,
                    expected_value="温柔",
                    description="声音应该体现温柔关怀",
                    evaluation_method="情感分析 - 语调轻柔，富有关怀",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.TIMBRE,
                    expected_value="柔和",
                    description="音色应该柔和圆润",
                    evaluation_method="音色分析或主观听感",
                    weight=0.3
                ),
            ],
            "知性": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.ARTICULATION,
                    expected_value="清晰准确",
                    description="发音应该清晰准确，体现知识性",
                    evaluation_method="发音分析 - 字正腔圆，逻辑清晰",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.SPEECH_RATE,
                    expected_value="适中",
                    description="语速应该适中，便于理解",
                    evaluation_method="计时分析或主观听感",
                    weight=0.2
                ),
            ],
            "时尚": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.EMOTION,
                    expected_value="时尚现代",
                    description="声音应该体现时尚感和现代感",
                    evaluation_method="情感分析 - 语调活泼，富有现代感",
                    weight=0.3
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.ARTICULATION,
                    expected_value="现代感",
                    description="表达方式应该符合现代年轻人的说话习惯",
                    evaluation_method="表达方式分析",
                    weight=0.3
                ),
            ],
            "浑厚": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.TIMBRE,
                    expected_value="浑厚有力",
                    description="音色应该浑厚有力，富有磁性",
                    evaluation_method="音色分析 - 低频丰富，共鸣感强",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.PITCH,
                    expected_value="低沉",
                    description="基频应该较低",
                    evaluation_method="基频分析或主观听感",
                    weight=0.3
                ),
            ],
            "译制腔": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.ARTICULATION,
                    expected_value="戏剧化",
                    description="发音应该有一定的戏剧化和夸张感",
                    evaluation_method="发音分析 - 语调起伏较大，富有表现力",
                    weight=0.4
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.EMOTION,
                    expected_value="表现力强",
                    description="情感表达应该丰富夸张",
                    evaluation_method="情感分析 - 情感变化明显",
                    weight=0.3
                ),
            ],
            "普通": [
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.ARTICULATION,
                    expected_value="标准",
                    description="发音应该标准自然",
                    evaluation_method="发音分析 - 接近普通话标准",
                    weight=0.3
                ),
                VerificationCriteria(
                    characteristic=VoiceCharacteristic.EMOTION,
                    expected_value="中性",
                    description="情感表达应该中性平和",
                    evaluation_method="情感分析 - 情感起伏较小",
                    weight=0.2
                ),
            ],
        }

        return criteria

    def _build_evaluation_questions(self) -> Dict[str, List[str]]:
        """Build specific evaluation questions for each characteristic"""
        questions = {
            "gender": [
                "听起来是男性还是女性声音？",
                "性别特征是否明显？",
                "是否存在性别模糊或矛盾？"
            ],
            "age": [
                "听起来像什么年龄段的人？（青年/中年/老年/少儿）",
                "年龄特征是否符合预期？",
                "语速和语调是否体现相应年龄特点？"
            ],
            "pitch": [
                "音调是高还是低？",
                "音调是否符合性别和年龄预期？",
                "音调是否自然流畅？"
            ],
            "speech_rate": [
                "语速是快还是慢？",
                "语速是否符合年龄特征？",
                "发音是否清晰可辨？"
            ],
            "emotion": [
                "声音传达了什么情感？",
                "情感是否与预期特征匹配？",
                "情感表达是否自然？"
            ],
            "timbre": [
                "音色是怎样的？（温暖/清亮/浑厚/柔和等）",
                "音色是否符合预期特征？",
                "音色是否悦耳自然？"
            ],
            "articulation": [
                "发音是否清晰准确？",
                "吐字是否标准？",
                "表达方式是否符合特征预期？"
            ]
        }

        return questions

    def get_criteria_for_seed(self, gender: str, age: str, features: List[str]) -> List[VerificationCriteria]:
        """Get verification criteria for a specific seed"""
        criteria_list = []

        # Add gender criteria
        if gender in self.criteria_database:
            criteria_list.extend(self.criteria_database[gender])

        # Add age criteria
        if age in self.criteria_database:
            criteria_list.extend(self.criteria_database[age])

        # Add feature criteria
        for feature in features:
            if feature in self.criteria_database:
                criteria_list.extend(self.criteria_database[feature])

        return criteria_list

    def create_evaluation_checklist(self, seed_id: str, gender: str, age: str, features: List[str]) -> str:
        """Create a detailed evaluation checklist for a seed"""
        criteria = self.get_criteria_for_seed(gender, age, features)

        checklist = f"=== 语音特征评估清单 ===\n"
        checklist += f"种子ID: {seed_id}\n"
        checklist += f"期望性别: {gender}\n"
        checklist += f"期望年龄: {age}\n"
        checklist += f"期望特征: {', '.join(features)}\n\n"

        # Group criteria by characteristic
        grouped_criteria = {}
        for criterion in criteria:
            char_name = criterion.characteristic.value
            if char_name not in grouped_criteria:
                grouped_criteria[char_name] = []
            grouped_criteria[char_name].append(criterion)

        # Create checklist sections
        for char_name, char_criteria in grouped_criteria.items():
            checklist += f"【{char_name.upper()} 评估】\n"
            checklist += f"权重: {sum(c.weight for c in char_criteria):.1f}\n\n"

            questions = self.evaluation_questions.get(char_name, [])
            for i, question in enumerate(questions, 1):
                checklist += f"{i}. {question}\n"
                checklist += f"   评分 (1-5): ___\n"
                checklist += f"   备注: _______\n\n"

            for criterion in char_criteria:
                checklist += f"标准: {criterion.description}\n"
                checklist += f"评估方法: {criterion.evaluation_method}\n"
                checklist += f"权重: {criterion.weight}\n\n"

            checklist += "---\n\n"

        checklist += "=== 总体评分 ===\n"
        total_weight = sum(c.weight for c in criteria)
        checklist += f"总权重: {total_weight:.1f}\n"
        checklist += "加权平均分: ____\n"
        checklist += "整体评价: _______\n"

        return checklist

    def print_all_criteria(self):
        """Print all available criteria"""
        print("=== 语音特征验证标准 ===\n")

        for category, criteria_list in self.criteria_database.items():
            print(f"【{category}】")
            for criterion in criteria_list:
                print(f"  - {criterion.characteristic.value}: {criterion.description}")
                print(f"    期望值: {criterion.expected_value}")
                print(f"    评估方法: {criterion.evaluation_method}")
                print(f"    权重: {criterion.weight}")
            print()

def main():
    """Main function to demonstrate the verification system"""
    verifier = VoiceVerificationSystem()

    # Print all criteria
    verifier.print_all_criteria()

    # Create example checklist for a seed
    print("=== 示例评估清单 ===")
    example_checklist = verifier.create_evaluation_checklist(
        seed_id="1283",
        gender="女",
        age="青年",
        features=["亲切"]
    )
    print(example_checklist)

if __name__ == "__main__":
    main()