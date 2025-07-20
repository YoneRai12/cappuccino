# image_generator.py

import torch
from diffusers import DiffusionPipeline
import tempfile
import os
from PIL import Image
import re
import subprocess
import random
import requests
import base64
from io import BytesIO

# 初回のみ数GBのモデルがDLされます（SDXL Turbo）
model_id = "stabilityai/sdxl-turbo"

# パイプラインを一度だけロード
try:
    print("Stable Diffusionパイプラインをロード中...")
    pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16")
    pipe = pipe.to("cuda")
    print("Stable Diffusionパイプラインのロード完了")
except Exception as e:
    print(f"パイプラインのロードに失敗: {e}")
    pipe = None

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

def stop_llm_process():
    # ollama, llama.cpp, python など関連プロセスをkill（Windows用）
    for proc in ["ollama.exe", "ollama", "llama.cpp.exe", "llama.cpp", "python.exe"]:
        try:
            subprocess.run(["taskkill", "/IM", proc, "/F"], check=False)
        except Exception as e:
            print(f"LLM停止失敗: {e}")

def start_llm_process():
    # 例: ollamaを再起動（Windows用）
    try:
        subprocess.Popen(["start", "", "ollama", "serve"], shell=True)
    except Exception as e:
        print(f"LLM再起動失敗: {e}")

def translate_to_english(text: str) -> str:
    # 超簡易辞書（本番はAPI推奨）
    if "猫" in text and "宇宙飛行士" in text:
        return "cat astronaut"
    if "犬" in text and "宇宙飛行士" in text:
        return "dog astronaut"
    if "りんご" in text or "林檎" in text:
        return "apple"
    if "バナナ" in text:
        return "banana"
    if "みかん" in text or "オレンジ" in text:
        return "orange"
    if "ぶどう" in text:
        return "grape"
    if "イチゴ" in text or "いちご" in text:
        return "strawberry"
    if "猫" in text:
        return "cat"
    if "犬" in text:
        return "dog"
    # 他にもパターン追加可
    return text  # fallback

def is_japanese(text: str) -> bool:
    """テキストに日本語が含まれているかチェック"""
    return bool(re.search(r'[ぁ-んァ-ン一-龥]', text))

def clean_for_sd(prompt: str) -> str:
    print(f"clean_for_sd開始: '{prompt}'")
    # コードブロックやJSONを除去
    prompt = re.sub(r'```.*?```', '', prompt, flags=re.DOTALL)
    prompt = re.sub(r'\{.*?\}', '', prompt, flags=re.DOTALL)
    prompt = re.sub(r'\[.*?\]', '', prompt, flags=re.DOTALL)
    
    # 「猫の画像を生成して」など命令文を「猫」だけに
    prompt = re.sub(r'の画像を生成して|を描いて|を作って|を出力して|を表示して', '', prompt)
    prompt = prompt.strip()
    
    # LLMの出力から実際のプロンプトを抽出
    # "Processed: ... 指示: " の形式から実際のプロンプトを抽出
    processed_match = re.search(r'指示:\s*(.+)', prompt, re.DOTALL)
    if processed_match:
        prompt = processed_match.group(1).strip()
        print(f"LLM出力から抽出: '{prompt}'")
    
    # prompt: xxx 形式ならxxxだけ抽出
    m = re.search(r'prompt\s*[:=]\s*([\w\W]+)', prompt)
    if m:
        prompt = m.group(1).strip()
        print(f"prompt形式から抽出: '{prompt}'")
    
    # {"prompt": "xxx"} 形式ならxxxだけ抽出
    m2 = re.search(r'"prompt"\s*:\s*"([^"]+)"', prompt)
    if m2:
        prompt = m2.group(1).strip()
        print(f"JSON形式から抽出: '{prompt}'")
    
    # 最後に、日本語の説明文が残っている場合は除去
    # 英語のプロンプト部分のみを抽出
    english_parts = []
    for line in prompt.split('\n'):
        line = line.strip()
        if line and not re.search(r'[ぁ-んァ-ン一-龥]', line):
            # 日本語が含まれていない行のみを追加
            english_parts.append(line)
    
    if english_parts:
        prompt = ' '.join(english_parts)
        print(f"英語部分のみ抽出: '{prompt}'")
    
    print(f"clean_for_sd完了: '{prompt}'")
    return prompt

def enhance_prompt(prompt: str) -> str:
    print(f"enhance_prompt開始: 元のプロンプト='{prompt}'")
    prompt = clean_for_sd(prompt)
    print(f"clean_for_sd後: '{prompt}'")
    
    # 英語の場合はLLM処理をスキップ
    if not is_japanese(prompt):
        result = f"{prompt}, a realistic photo, natural lighting, high detail, 4K, soft focus, shallow depth of field"
        print(f"英語プロンプト処理: '{result}'")
        return result
    
    # 日本語の場合は簡易辞書で英語に変換
    english_prompt = translate_to_english(prompt)
    print(f"日本語→英語変換: '{prompt}' → '{english_prompt}'")
    
    # ランダム性を確実にするためにseedをリセット
    random.seed()
    
    # LLMでランダムなプロンプト生成（ここでは簡易的にランダムな形容詞を追加）
    random_adjectives = [
        "beautiful", "stunning", "gorgeous", "magnificent", "elegant", 
        "charming", "delightful", "wonderful", "amazing", "fantastic",
        "breathtaking", "spectacular", "exquisite", "lovely", "graceful"
    ]
    random_style = random.choice(random_adjectives)
    print(f"ランダム形容詞選択: '{random_style}'")
    
    result = f"{english_prompt}, {random_style}, a realistic photo, natural lighting, high detail, 4K, soft focus, shallow depth of field"
    print(f"最終プロンプト: '{result}'")
    return result

# generate_imageの引数promptは自然文でOK
# 関数内部で必要に応じてJSONプロンプトを自動生成し、Stable Diffusionに渡す
def generate_image(prompt: str, options: dict = None) -> str:
    print("generate_image: stop_llm_process前")
    # stop_llm_process()  # ←一時的にコメントアウト
    print("generate_image: free_llm_vram前")
    # free_llm_vram()     # ←一時的にコメントアウト
    print(f"generate_image呼び出し: {prompt}")
    if pipe is None:
        raise RuntimeError("Stable Diffusionパイプラインがロードされていません")
    if options is None:
        options = {}
    enhanced_prompt = enhance_prompt(prompt)
    num_inference_steps = options.get("num_inference_steps", 30) if options else 30
    guidance_scale = options.get("guidance_scale", 7.0) if options else 7.0
    
    # ランダム性を確実にするためにseedをリセット
    random.seed()
    # seedをランダムに設定（Noneの場合はランダム）
    seed = options.get("seed", random.randint(1, 1000000)) if options else random.randint(1, 1000000)
    print(f"生成されたseed: {seed}")
    
    width = options.get("width", 512) if options else 512
    height = options.get("height", 512) if options else 512
    generator = torch.manual_seed(seed) if seed is not None else None
    print(f"画像生成中: prompt='{enhanced_prompt}', steps={num_inference_steps}, scale={guidance_scale}, seed={seed}, width={width}, height={height}")
    print("画像生成パイプライン呼び出し直前")
    image = pipe(
        prompt=enhanced_prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator,
        width=width,
        height=height
    ).images[0]
    print("画像生成パイプライン呼び出し直後")
    print("画像生成処理完了")
    
    # リサイズ制限を削除 - 高解像度を維持
    print(f"生成された画像サイズ: {width}x{height}")
    
    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

def generate_image_with_negative(prompt: str, negative_prompt: str, options: dict = None) -> str:
    """ネガティブプロンプト付きで画像生成"""
    print(f"generate_image_with_negative呼び出し: prompt='{prompt}', negative='{negative_prompt}'")
    if pipe is None:
        raise RuntimeError("Stable Diffusionパイプラインがロードされていません")
    if options is None:
        options = {}
    
    # プロンプトをクリーンアップ
    enhanced_prompt = clean_for_sd(prompt)
    enhanced_negative = clean_for_sd(negative_prompt)
    
    num_inference_steps = options.get("num_inference_steps", 30) if options else 30
    guidance_scale = options.get("guidance_scale", 7.0) if options else 7.0
    
    # ランダム性を確実にするためにseedをリセット
    random.seed()
    # seedをランダムに設定（Noneの場合はランダム）
    seed = options.get("seed", random.randint(1, 1000000)) if options else random.randint(1, 1000000)
    print(f"生成されたseed: {seed}")
    
    width = options.get("width", 512) if options else 512
    height = options.get("height", 512) if options else 512
    generator = torch.manual_seed(seed) if seed is not None else None
    
    print(f"画像生成中: prompt='{enhanced_prompt}', negative='{enhanced_negative}', steps={num_inference_steps}, scale={guidance_scale}, seed={seed}, width={width}, height={height}")
    print("画像生成パイプライン呼び出し直前")
    
    image = pipe(
        prompt=enhanced_prompt,
        negative_prompt=enhanced_negative,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator,
        width=width,
        height=height
    ).images[0]
    
    print("画像生成パイプライン呼び出し直後")
    print("画像生成処理完了")
    
    # リサイズ制限を削除 - 高解像度を維持
    print(f"生成された画像サイズ: {width}x{height}")
    
    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    # 高品質で保存（ファイルサイズを抑えるため）
    image.save(fp, "PNG", optimize=True, quality=85)
    fp.close()
    
    # ファイルサイズをチェック
    file_size = os.path.getsize(fp.name) / (1024 * 1024)  # MB
    print(f"保存されたファイルサイズ: {file_size:.2f}MB")
    
    del image
    torch.cuda.empty_cache()
    return fp.name

def upload_to_imgur(image_path: str, client_id: str = None) -> str:
    """画像をImgurにアップロードしてURLを取得"""
    try:
        # Imgur APIを使用（無料版）
        upload_url = "https://api.imgur.com/3/image"
        
        with open(image_path, "rb") as image_file:
            files = {'image': image_file}
            headers = {}
            
            # クライアントIDが設定されている場合
            if client_id:
                headers['Authorization'] = f'Client-ID {client_id}'
            
            response = requests.post(upload_url, files=files, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data['data']['link']
            else:
                print(f"Imgurアップロード失敗: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"Imgurアップロードエラー: {e}")
        return None

def upload_to_imgbb(image_path: str, api_key: str = None) -> str:
    """画像をImgBBにアップロードしてURLを取得（APIキー不要）"""
    try:
        upload_url = "https://api.imgbb.com/1/upload"
        
        with open(image_path, "rb") as image_file:
            files = {'image': image_file}
            data = {}
            
            # APIキーが設定されている場合
            if api_key:
                data['key'] = api_key
            
            response = requests.post(upload_url, files=files, data=data)
            
            if response.status_code == 200:
                data = response.json()
                return data['data']['url']
            else:
                print(f"ImgBBアップロード失敗: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"ImgBBアップロードエラー: {e}")
        return None
