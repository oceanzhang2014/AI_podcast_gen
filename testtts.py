#项目代码和视频由AI超元域频道原创，禁止盗搬

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

def run_chattts(text):
    command = f"chattts -s 2 '{text}'"
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Output: {e.stdout.decode('utf-8')}")
        print(f"Error: {e.stderr.decode('utf-8')}")
        return None

# 测试
text = "你好啊，今天天气怎么样呢。"
output = run_chattts(text)
if output:
    print(output)