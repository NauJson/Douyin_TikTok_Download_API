import os
import whisper
import subprocess
from moviepy.editor import VideoFileClip
import requests
import sys
import time
from enum import Enum

VIDEO_DIR = 'download/douyin_video'
AUDIO_DIR = 'video-analyzer/audio'
OUTPUT_DIR = 'video-analyzer/output'

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# whisper_model = whisper.load_model("base")  # 移除原有的顶层加载
whisper_model = None  # 用于懒加载

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model

class ModelConfig(Enum):
    OLLAMA_QWEN2_1_5B = {
        'model': 'ollama',
        'model_name': 'qwen2:1.5b',
        'api_key': None,
        'api_url': None
    }
    OLLAMA_QWEN3_4B = {
        'model': 'ollama',
        'model_name': 'qwen3:4b',
        'api_key': None,
        'api_url': None
    }
    OLLAMA_QWEN2_5_1_5B = {
        'model': 'ollama',
        'model_name': 'qwen2.5:1.5b',
        'api_key': None,
        'api_url': None
    }
    OLLAMA_QWEN2_5_7B = {
        'model': 'ollama',
        'model_name': 'qwen2.5:7b',
        'api_key': None,
        'api_url': None
    }
    GEMINI = {
        'model': 'gemini',
        'model_name': None,
        'api_key': 'AIzaSyAdTGRH0AxltEyN-aJF63AtHySBoKur5Go',
        'api_url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyAdTGRH0AxltEyN-aJF63AtHySBoKur5Go'
    }
    OPENAI_GPT4O_MINI = {
        'model': 'openai',
        'model_name': 'gpt-4o-mini',
        'api_key': 'sk-JB3VXVi3JcHpz0ZIKUrJeE6rYrE03tQSmKw4NHoRPtG3wbAA',
        # 'api_url': 'https://api.openai.com/v1/chat/completions'
        'api_url': 'https://api.chatanywhere.tech/v1/chat/completions'
    }

def extract_audio(video_path, audio_path):
    print(f"[音频提取] {video_path} -> {audio_path}")
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, verbose=False, logger=None)

def transcribe_audio(audio_path):
    print(f"[语音转写] {audio_path}")
    model = get_whisper_model()
    result = model.transcribe(audio_path, language='zh')
    return result['text']

def analyze_with_ollama(transcript_text, model_name):
    prompt = f"""
请根据以下文字内容进行优化：

{transcript_text}

要求输出：
1. 仅根据上下文，调整分语言隔符
2. 为确保语义通顺情况下，可以调整部分单词
3. 【禁止】禁止添加任何其他内容
"""
    print("[调用 Ollama 模型分析]")
    for attempt in range(10):
        try:
            result = subprocess.run(
                ["ollama", "run", model_name],
                input=prompt,
                text=True,
                capture_output=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            else:
                print(f"[Ollama 调用失败] 第{attempt+1}次，30秒后重试…")
        except Exception as e:
            print(f"[Ollama 调用异常] 第{attempt+1}次，30秒后重试… 错误: {e}")
        if attempt < 9:
            time.sleep(30)
    return "[Ollama 模型调用失败，已重试10次]"

def analyze_with_gemini(transcript_text, api_key, api_url):
    prompt = f"""
请根据以下视频音频转写内容进行分析：

{transcript_text}

要求输出：
1. 输出内容是给学生和学生家长看的
2. 视频内容摘要（不超过100字）
3. 提取3个核心观点
4. 给出3个合适的短视频话题标签（如 #健康 #亲子 #创业）
5. 给学生和家长一句建议（以\"建议你……\"开头）
"""
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    print("[调用 Google Gemini 2.0 分析]")
    for attempt in range(10):
        try:
            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                try:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    print(f"[Gemini API 返回解析失败] 第{attempt+1}次，30秒后重试… 错误: {e}")
            else:
                print(f"[Gemini API 请求失败] 状态码: {response.status_code} 第{attempt+1}次，30秒后重试…")
        except Exception as e:
            print(f"[Gemini API 请求异常] 第{attempt+1}次，30秒后重试… 错误: {e}")
        if attempt < 9:
            time.sleep(30)
    return "[Gemini API 调用失败，已重试10次]"

def analyze_with_openai(transcript_text, api_key, api_url, model_name):
    """
    通用 OpenAI Chat API 调用方法，支持任意 chat 模型。
    扩展 openai 模型时，只需在 ModelConfig 中新增配置，并传递对应参数。
    """
    prompt = f"""
请根据以下视频音频转写内容进行分析：

{transcript_text}

要求输出：
1. 输出内容是给学生和学生家长看的
2. 视频内容摘要（不超过100字）
3. 提取3个核心观点
4. 给出3个合适的短视频话题标签（如 #健康 #亲子 #创业）
5. 给学生和家长一句建议（以\"建议你……\"开头）
"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "你是一个专业的视频内容分析助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    print(f"[调用 OpenAI {model_name} 分析]")
    for attempt in range(10):
        try:
            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                try:
                    return result["choices"][0]["message"]["content"]
                except Exception as e:
                    print(f"[OpenAI API 返回解析失败] 第{attempt+1}次，30秒后重试… 错误: {e}")
            else:
                print(f"[OpenAI API 请求失败] 状态码: {response.status_code} 第{attempt+1}次，30秒后重试…")
        except Exception as e:
            print(f"[OpenAI API 请求异常] 第{attempt+1}次，30秒后重试… 错误: {e}")
        if attempt < 9:
            time.sleep(30)
    return "[OpenAI API 调用失败，已重试10次]"

def analyze_with_model(transcript_text, model_config):
    model = model_config.value['model']
    if model == "gemini":
        return analyze_with_gemini(transcript_text, model_config.value['api_key'], model_config.value['api_url'])
    elif model == "openai":
        return analyze_with_openai(transcript_text, model_config.value['api_key'], model_config.value['api_url'], model_config.value['model_name'])
    else:
        return analyze_with_ollama(transcript_text, model_config.value['model_name'])

def process_video(file_path, model_config):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    audio_path = os.path.join(AUDIO_DIR, base_name + ".wav")
    output_path = os.path.join(OUTPUT_DIR, base_name + ".md")

    extract_audio(file_path, audio_path)
    transcript = transcribe_audio(audio_path)
    print(transcript)
    analysis = analyze_with_model(transcript, model_config)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# 视频分析报告 - {base_name}\n\n")
        f.write("## 🎧 音频转写内容：\n\n")
        f.write(transcript + "\n\n")
        f.write("## 🤖 大模型分析结果：\n\n")
        f.write(analysis)
    print(f"[✅ 报告已生成] {output_path}\n")

def main(model_config: ModelConfig):
    # 选择模型
    model_map = {
        ModelConfig.OLLAMA_QWEN3_4B: ModelConfig.OLLAMA_QWEN3_4B,
        ModelConfig.OLLAMA_QWEN2_5_1_5B: ModelConfig.OLLAMA_QWEN2_5_1_5B,
        ModelConfig.OLLAMA_QWEN2_5_7B: ModelConfig.OLLAMA_QWEN2_5_7B,
        ModelConfig.GEMINI: ModelConfig.GEMINI,
        ModelConfig.OLLAMA_QWEN2_1_5B: ModelConfig.OLLAMA_QWEN2_1_5B,
        ModelConfig.OPENAI_GPT4O_MINI: ModelConfig.OPENAI_GPT4O_MINI
    }
    if model_config not in model_map:
        print("[警告] 未知模型参数，默认使用 OLLAMA_QWEN2_1_5B。可选参数：ollama、ollama-qwen2:1.5b、ollama-qwen3:4b、ollama-qwen2.5:1.5b、ollama-qwen2.5:7b、gemini、openai")
        model_config = ModelConfig.OLLAMA_QWEN2_1_5B

    video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith((".mp4", ".MP4", ".mov"))]
    total = len(video_files)
    print(f"共检测到 {total} 个视频文件。\n")
    for idx, file_name in enumerate(video_files, 1):
        base_name = os.path.splitext(file_name)[0]
        output_path = os.path.join(OUTPUT_DIR, base_name + ".md")
        if os.path.exists(output_path):
            print(f"[跳过] 已存在报告，跳过：{file_name}")
            continue
        print(f"[进度] 正在处理第 {idx}/{total} 个视频：{file_name}")
        video_path = os.path.join(VIDEO_DIR, file_name)
        process_video(video_path, model_config)

def analyze_video_file(file_path, model_config):
    """
    分析单个视频文件，返回大模型总结，并自动删除音频和视频文件。
    :param file_path: 视频文件路径
    :param model_config: ModelConfig 枚举
    :return: str 大模型总结内容
    """
    import shutil
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    audio_path = os.path.join(AUDIO_DIR, base_name + ".wav")
    output_path = os.path.join(OUTPUT_DIR, base_name + ".md")
    try:
        extract_audio(file_path, audio_path)
        transcript = transcribe_audio(audio_path)
        summary = analyze_with_model(transcript, model_config)
        # 写入 markdown 文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 视频分析报告 - {base_name}\n\n")
            f.write("## 🎧 音频转写内容：\n\n")
            f.write(transcript + "\n\n")
            f.write("## 🤖 大模型分析结果：\n\n")
            f.write(summary)
        return summary
    finally:
        # 删除音频和视频文件
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    # 支持命令行参数选择模型（用枚举名）
    model_enum = ModelConfig.OLLAMA_QWEN2_5_7B
    if len(sys.argv) > 1:
        try:
            model_enum = ModelConfig[sys.argv[1]]
        except KeyError:
            print(f"[警告] 未知模型参数，默认使用 OLLAMA_QWEN2_1_5B。可选参数：{', '.join([m.name for m in ModelConfig])}")
    main(model_enum)
