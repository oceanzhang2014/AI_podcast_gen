#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows兼容版音频生成脚本
"""

import os
import sys
import time
import argparse
from pathlib import Path

# 设置Windows控制台编码
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# 尝试导入ChatTTS
try:
    import ChatTTS
    import torch
    import torchaudio
    CHATTTS_AVAILABLE = True
except ImportError:
    CHATTTS_AVAILABLE = False
    print("警告: ChatTTS未安装或未找到，请先安装ChatTTS")
    print("   pip install ChatTTS")

def generate_audio_with_seed(seed_id: str, text: str, output_path: str = None) -> bool:
    """
    使用指定种子生成音频 (基于talk.py的优化方法)
    """
    if not CHATTTS_AVAILABLE:
        print("错误: ChatTTS不可用，无法生成音频")
        return False

    try:
        # 设置默认输出路径
        if not output_path:
            timestamp = int(time.time())
            output_path = f"audio_seed_{seed_id}_{timestamp}.wav"

        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"种子ID: {seed_id}")
        print(f"文本: {text}")
        print(f"输出文件: {output_path}")
        print("正在生成音频...")

        # === 基于talk.py的优化方法 ===
        # 1. 每次都重新初始化ChatTTS实例 (关键改进)
        print("初始化ChatTTS实例...")
        chat = ChatTTS.Chat()

        # 2. 加载模型
        try:
            chat.load(compile=False)
            print("✅ 模型加载成功")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            print("请确保ChatTTS模型已正确下载和配置")
            return False

        # 3. 完整的种子设置 (基于talk.py方法)
        seed_int = int(seed_id)
        print(f"设置种子: {seed_int}")

        # 设置所有相关的随机种子
        torch.manual_seed(seed_int)
        torch.random.manual_seed(seed_int)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed_int)
            torch.cuda.manual_seed_all(seed_int)

        # 设置Python和numpy的随机种子
        import random
        import numpy as np
        random.seed(seed_int)
        np.random.seed(seed_int)

        # 尝试ChatTTS的种子方法
        try:
            chat.seed([seed_int])
            print("✅ 使用 chat.seed([int]) 方法")
        except (AttributeError, TypeError) as e1:
            try:
                chat.seed(seed_int)
                print("✅ 使用 chat.seed(int) 方法")
            except (AttributeError, TypeError) as e2:
                print(f"⚠️  ChatTTS种子方法失败，使用手动设置: {e2}")

        print("✅ 种子设置完成")

        # 4. 生成音频
        print("开始生成音频...")
        texts = [text]
        wavs = None

        # 尝试不同的生成参数
        try:
            wavs = chat.infer(texts, use_decoder=True)
            print("✅ 使用 use_decoder=True 生成音频")
        except Exception as e1:
            print(f"⚠️  use_decoder=True 失败: {e1}")

            try:
                wavs = chat.infer(texts, use_decoder=True, skip_refine_text=False)
                print("✅ 使用 skip_refine_text=False 生成音频")
            except Exception as e2:
                print(f"⚠️  skip_refine_text=False 失败: {e2}")

                try:
                    wavs = chat.infer(texts)
                    print("✅ 使用基础参数生成音频")
                except Exception as e3:
                    print(f"❌ 所有生成方法都失败了: {e3}")
                    return False

        # 5. 验证和处理音频数据
        if wavs is None or len(wavs) == 0:
            print("❌ 错误: 没有生成音频数据")
            return False

        print("✅ 音频数据生成成功")

        # 处理音频数据格式
        audio_data = wavs[0] if isinstance(wavs, list) else wavs
        if isinstance(audio_data, list):
            audio_data = audio_data[0]

        # 验证音频数据
        if not hasattr(audio_data, '__len__') or len(audio_data) == 0:
            print("❌ 错误: 音频数据为空")
            return False

        # 转换为tensor
        if not isinstance(audio_data, torch.Tensor):
            audio_tensor = torch.from_numpy(audio_data)
        else:
            audio_tensor = audio_data

        # 确保是2D tensor (channels, samples)
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)

        print(f"✅ 音频数据处理完成，形状: {audio_tensor.shape}")

        # 6. 保存音频文件
        torchaudio.save(str(output_path), audio_tensor, 24000)

        # 验证保存结果
        if output_path.exists():
            file_size = output_path.stat().st_size
            if file_size > 0:
                print(f"✅ 音频生成成功: {output_path}")
                print(f"✅ 文件大小: {file_size} bytes")
                return True
            else:
                print("❌ 错误: 生成的音频文件为空")
                return False
        else:
            print("❌ 错误: 音频文件未保存")
            return False

    except Exception as e:
        print(f"❌ 生成音频时出错: {e}")
        print("请检查:")
        print("   1. ChatTTS是否正确安装")
        print("   2. 模型是否已下载")
        print("   3. 文本内容是否合适")
        print("   4. 系统是否有足够的内存")
        return False

def show_available_seeds():
    """显示可用的种子"""
    try:
        from seed_database import SEED_DATABASE, print_seed_table
        print("\n可用种子列表:")
        print("="*60)
        print_seed_table()
        print("="*60)
    except ImportError:
        print("无法加载种子数据库")
        # 显示一些常用种子
        print("\n常用种子:")
        print("1283 - 青年女性亲切声音")
        print("2241 - 中年女性温柔知性声音")
        print("731 - 青年女性成熟声音")
        print("579 - 中年男性浑厚声音")
        print("2550 - 青年男性时尚声音")

def main():
    parser = argparse.ArgumentParser(
        description="使用ChatTTS生成音频 (Windows兼容版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python generate_audio_win.py --seed 1283 --text "你好，这是测试音频"
  python generate_audio_win.py --seed 2241 --text "欢迎收听今天的节目" --output welcome.wav
  python generate_audio_win.py --list-seeds
  python generate_audio_win.py --interactive
        """
    )

    parser.add_argument("--seed", help="种子ID (例如: 1283)")
    parser.add_argument("--text", help="要合成的文本")
    parser.add_argument("--output", help="输出文件名 (可选)")
    parser.add_argument("--list-seeds", action="store_true", help="显示可用种子")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")

    args = parser.parse_args()

    if args.list_seeds:
        show_available_seeds()
        return

    if args.interactive:
        print("ChatTTS 音频生成工具 (Windows兼容版)")
        print("="*50)

        if not CHATTTS_AVAILABLE:
            print("错误: ChatTTS不可用，请先安装:")
            print("   pip install ChatTTS")
            return

        show_available_seeds()

        while True:
            print("\n" + "-"*40)
            seed_input = input("请输入种子ID (或 'quit' 退出): ").strip()

            if seed_input.lower() in ['quit', 'exit', 'q']:
                print("再见!")
                break

            if not seed_input:
                print("请输入有效的种子ID")
                continue

            text_input = input("请输入要合成的文本: ").strip()

            if not text_input:
                print("请输入要合成的文本")
                continue

            output_input = input("输出文件名 (回车使用默认): ").strip()
            output_path = output_input if output_input else None

            # 生成音频
            success = generate_audio_with_seed(seed_input, text_input, output_path)

            if success:
                choice = input("\n继续生成? (y/n): ").strip().lower()
                if choice not in ['y', 'yes', '是']:
                    print("再见!")
                    break
            else:
                choice = input("\n生成失败，是否重试? (y/n): ").strip().lower()
                if choice not in ['y', 'yes', '是']:
                    break

    else:
        # 命令行模式
        if not args.seed or not args.text:
            print("错误: 请提供种子ID和文本")
            print("使用 --help 查看帮助信息")
            print("使用 --list-seeds 查看可用种子")
            print("使用 --interactive 进入交互模式")
            sys.exit(1)

        success = generate_audio_with_seed(args.seed, args.text, args.output)
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()