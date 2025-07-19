# image_generator.py

import torch
from diffusers import DiffusionPipeline
import tempfile
import os
from PIL import Image
import re

# 初回のみ数GBのモデルがDLされます（SDXL Turbo）
model_id = "stabilityai/sdxl-turbo"

# パイプラインを一度だけロード
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16")
pipe = pipe.to("cuda")

def free_llm_vram():
    try:
        from docker_tools import nvidia_smi_clear_memory
        nvidia_smi_clear_memory()
    except Exception as e:
        print(f"LLM VRAM開放失敗: {e}")
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

def translate_to_english(text: str) -> str:
    # 超簡易辞書（本番はAPI推奨）
    if "猫" in text and "宇宙飛行士" in text:
        return "cat astronaut"
    if "犬" in text and "宇宙飛行士" in text:
        return "dog astronaut"
    if "猫" in text:
        return "cat"
    if "犬" in text:
        return "dog"
    # 他にもパターン追加可
    return text  # fallback

def clean_for_sd(prompt: str) -> str:
    # コードブロックやJSONを除去
    prompt = re.sub(r'```.*?```', '', prompt, flags=re.DOTALL)
    prompt = re.sub(r'\{.*?\}', '', prompt, flags=re.DOTALL)
    prompt = re.sub(r'\[.*?\]', '', prompt, flags=re.DOTALL)
    # 「猫の画像を生成して」など命令文を「猫」だけに
    prompt = re.sub(r'の画像を生成して|を描いて|を作って|を出力して|を表示して', '', prompt)
    prompt = prompt.strip()
    # prompt: xxx 形式ならxxxだけ抽出
    m = re.search(r'prompt\s*[:=]\s*([\w\W]+)', prompt)
    if m:
        prompt = m.group(1).strip()
    # {"prompt": "xxx"} 形式ならxxxだけ抽出
    m2 = re.search(r'"prompt"\s*:\s*"([^"]+)"', prompt)
    if m2:
        prompt = m2.group(1).strip()
    return prompt

def enhance_prompt(prompt: str) -> str:
    prompt = clean_for_sd(prompt)
    # 日本語なら英訳
    if re.search(r'[ぁ-んァ-ン一-龥]', prompt):
        prompt = translate_to_english(prompt)
    return f"{prompt}, a realistic photo, natural lighting, high detail, 4K, soft focus, shallow depth of field"

def generate_image(prompt: str, options: dict = None) -> str:
    """
    ユーザーのプロンプトに基づいて画像を生成します。
    任意でオプションパラメータも受け取れます。
    """
    if options is None:
        options = {}

    # 画像生成前にVRAM開放
    free_llm_vram()

    # プロンプトを写実的・自然な猫に強化
    enhanced_prompt = enhance_prompt(prompt)

    num_inference_steps = options.get("num_inference_steps", 30)
    guidance_scale = options.get("guidance_scale", 7.0)
    seed = options.get("seed", None)

    generator = torch.manual_seed(seed) if seed is not None else None

    print(f"画像生成中: prompt='{enhanced_prompt}', steps={num_inference_steps}, scale={guidance_scale}, seed={seed}")
    image = pipe(
        prompt=enhanced_prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator
    ).images[0]

    # 一時ファイルに保存
    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    image.save(fp, "PNG")
    fp.close()
    return fp.name
