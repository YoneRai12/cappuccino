# image_generator.py

import torch
from diffusers import DiffusionPipeline
import tempfile
import os
from PIL import Image

# 初回のみ数GBのモデルがDLされます（SDXL Turbo）
model_id = "stabilityai/sdxl-turbo"

# パイプラインを一度だけロード
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16")
pipe = pipe.to("cuda")

def generate_image(prompt: str, options: dict = None) -> str:
    """
    ユーザーのプロンプトに基づいて画像を生成します。
    任意でオプションパラメータも受け取れます。

    Args:
        prompt (str): 画像の説明テキスト（英語推奨）
        options (dict): 以下のキーを含む任意のパラメータ
            - width (int): 画像の幅（未使用：SDXL Turboは固定サイズ推奨）
            - height (int): 画像の高さ（未使用）
            - num_inference_steps (int): 推論ステップ数（デフォルト: 1）
            - guidance_scale (float): ガイダンススケール（デフォルト: 0.0）
            - seed (int): 乱数シード（指定時、再現性のある生成）

    Returns:
        str: 保存された画像ファイルのパス
    """
    if options is None:
        options = {}

    num_inference_steps = options.get("num_inference_steps", 1)
    guidance_scale = options.get("guidance_scale", 0.0)
    seed = options.get("seed", None)

    generator = torch.manual_seed(seed) if seed is not None else None

    print(f"画像生成中: prompt='{prompt}', steps={num_inference_steps}, scale={guidance_scale}, seed={seed}")
    image = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator
    ).images[0]

    # 一時ファイルに保存
    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    image.save(fp, "PNG")
    fp.close()

    print(f"✅ 画像生成完了: {fp.name}")
    return fp.name
