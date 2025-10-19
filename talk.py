# 男性

# Seed	age	style
# 111	young	Literary
# 333	young	Gentle
# 666	middle-aged	White-collar
# 7777	middle-aged	Hong Kong-style
# 9999	middle-aged	Deep and resonant
# 女性

# Seed	age	style
# 2	young	Emotionally rich
# 4	middle-aged	Deeply emotional
# 1111	middle-aged	Clear and pure
# 3333	middle-aged	Calm and serene
import subprocess
import shlex
from pydub import AudioSegment
import os
from autogen import ConversableAgent
from datetime import datetime




def run_chattts(text, output_file, speaker_index):
    # 对文本进行转义和格式化
    escaped_text = shlex.quote(text)
    
    # 根据说话者的索引选择不同的声音参数
    if speaker_index % 2 == 0:
        voice_param = "-s 2"  # 女性声音
    else:
        voice_param = "-s 333"  # 男性声音
    
    command = f"chattts {voice_param} -o {output_file} {escaped_text}"
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")


llm3 = {
    "config_list": [
        {
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "sk-ccb8d787d11c44b98a884424a682bd2c",
        },
    ],
    "cache_seed": None,  # Disable caching.
}




Darcy = ConversableAgent(
    "Darcy",
    llm_config=llm3,
    system_message="你是《傲慢与偏见》中的男主角达西先生。你是一位富有、高傲但内心善良的绅士。你对伊丽莎白的智慧和独立性格印象深刻,但又常常被她的言语所挑战。请根据伊丽莎白的发言,以达西的口吻和性格进行回应。",
)
Elizabeth = ConversableAgent(
    "Elizabeth",
    llm_config=llm3,
    system_message="你是《傲慢与偏见》中的女主角伊丽莎白。你是一位聪慧、独立且性格开朗的年轻女性。你对达西先生的傲慢和自负初impression不佳,但渐渐被他的真诚和善良所吸引。请根据达西先生的发言,以伊丽莎白的口吻和性格进行回应。",
)

chat_result = Elizabeth.initiate_chat(Darcy, message="达西先生,我们在上次的舞会上初次见面,我对您的第一印象是傲慢和自负。您几乎没有和任何女士跳舞,只是站在那里评判别人。我想知道,您为什么给人这样的印象?您真的如此高傲,还是有什么其他的原因?请告诉我您的想法。", max_turns=6)



# 指定 ffmpeg 的路径
# AudioSegment.converter = "C:\\Program Files\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe"

# 假设 chat_result.chat_history 是一个包含消息的列表
chat_history = chat_result.chat_history
# 创建一个空的 AudioSegment 对象，用于存储合并后的音频
combined_audio = AudioSegment.empty()

# 用于存储生成的音频文件名的列表
generated_files = []
# 生成音频文件
for i, message in enumerate(chat_history):
    text = message["content"]
    output_file = f"output_{i}.wav"
    run_chattts(text, output_file, i)
    # 加载生成的音频文件并合并到 combined_audio
    audio = AudioSegment.from_wav(output_file)
    combined_audio += audio   
    # 将生成的文件名添加到列表中
    generated_files.append(output_file)     
    # 导出合并后的音频文件
# 生成带有时间戳的文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  
combined_output_file = f"combined_output_{timestamp}.wav" 
# 导出合并后的音频文件
combined_audio.export(combined_output_file, format="wav")
# 删除单独的 WAV 文件
for file in generated_files:
    os.remove(file)