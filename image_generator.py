# image_generator.py
import torch
from diffusers import DiffusionPipeline
import tempfile
import os
from PIL import Image

# このモデルは初回実行時に自動でダウンロードされます（数GBあります）
model_id = "stabilityai/sdxl-turbo"

# パイプラインを一度だけロードして、再利用できるようにする
# これにより、毎回モデルをロードする時間を節約できます
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16")
pipe = pipe.to("cuda")

def generate_image(prompt: str) -> str:
    """
    ユーザーの指示（プロンプト）に基づいて画像を生成します。
    Generates an image from a user's prompt.
    Args:
        prompt (str): 画像の内容を説明するテキスト。英語が望ましいです。
                      A text description of the image content, preferably in English.
    Returns:
        str: 生成された画像が保存されている一時ファイルのパス。
             The path to the temporary file where the generated image is saved.
    """
    print(f"画像生成を開始します... プロンプト: '{prompt}'")
    
    # 高速化のための推論ステップ数を設定（Turboモデルの場合）
    image = pipe(prompt=prompt, num_inference_steps=1, guidance_scale=0.0).images[0]

    # 一時ファイルに画像を保存
    # delete=Falseにしないと、ファイルを閉じた瞬間に消えてしまう
    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    image.save(fp, "PNG")
    fp.close()
    
    print(f"画像の生成が完了しました。パス: {fp.name}")
    return fp.name