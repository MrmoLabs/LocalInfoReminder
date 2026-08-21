import os
from gtts import gTTS

def generate_audio(text, filename, lang='zh-cn'):
    print(f"Generating {filename} for text: '{text}'...")
    tts = gTTS(text=text, lang=lang)
    # Save as mp3
    save_path = os.path.join("assets", filename)
    tts.save(save_path)
    print(f"Saved to {save_path}")

def main():
    if not os.path.exists("assets"):
        os.makedirs("assets")

    # 1. Numbers 1-10
    for i in range(1, 11):
        generate_audio(f"{i}号", f"{i}hao.mp3")

    # 2. Actions
    generate_audio("准备", "prepare.mp3")
    generate_audio("释放", "release.mp3")

    # 3. Events
    generate_audio("事件出现", "wild_spawn.mp3")
    generate_audio("关键目标出现", "dragon_spawn.mp3")

    # 4. System Sounds
    generate_audio("滴", "tick.mp3")
    generate_audio("叮", "ding.mp3")
    generate_audio("重置", "reset.mp3")
    generate_audio("取消", "cancel.mp3")
    
    # Extra for LogicEngine compatibility
    generate_audio("开始", "start.mp3") 
    generate_audio("技能提醒", "enemy_cd.mp3")

if __name__ == "__main__":
    main()
