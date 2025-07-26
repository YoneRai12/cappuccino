"""Llama 3.1-latest + Stable Diffusion API テストスクリプト"""

import asyncio
import aiohttp
import json
from typing import Dict, Any


class APITester:
    """APIテストクラス"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health(self) -> Dict[str, Any]:
        """ヘルスチェックテスト"""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()
    
    async def test_llama_chat(self, prompt: str, model: str = "llama-3.1-latest") -> Dict[str, Any]:
        """Llama 3.1-latestチャットテスト"""
        data = {
            "prompt": prompt,
            "model": model,
            "temperature": 0.8,
            "max_tokens": 2048
        }
        
        async with self.session.post(f"{self.base_url}/llm/chat", json=data) as response:
            return await response.json()
    
    async def test_image_generation(self, prompt: str) -> Dict[str, Any]:
        """Stable Diffusion画像生成テスト"""
        data = {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality",
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg_scale": 7.5
        }
        
        async with self.session.post(f"{self.base_url}/image/generate", json=data) as response:
            return await response.json()
    
    async def test_generate_with_image(self, prompt: str, model: str = "llama-3.1-latest") -> Dict[str, Any]:
        """Llama 3.1-latest+Stable Diffusion画像生成テスト"""
        data = {
            "prompt": prompt,
            "model": model,
            "temperature": 0.8,
            "max_tokens": 2048
        }
        
        async with self.session.post(f"{self.base_url}/llm/generate_with_image", json=data) as response:
            return await response.json()
    
    async def test_chat(self, message: str, model: str = "llama-3.1-latest") -> Dict[str, Any]:
        """Llama 3.1-latestシンプルチャットテスト"""
        data = {
            "message": message,
            "model": model
        }
        
        async with self.session.post(f"{self.base_url}/chat", json=data) as response:
            return await response.json()
    
    async def test_models(self) -> Dict[str, Any]:
        """モデル一覧テスト"""
        async with self.session.get(f"{self.base_url}/models") as response:
            return await response.json()


async def run_tests():
    """テスト実行"""
    print("🚀 Llama 3.1-latest + Stable Diffusion APIテストを開始します...")
    
    async with APITester() as tester:
        # ヘルスチェック
        print("\n📊 ヘルスチェック...")
        health = await tester.test_health()
        print(f"ヘルスチェック結果: {json.dumps(health, indent=2, ensure_ascii=False)}")
        
        # モデル一覧
        print("\n🤖 モデル一覧...")
        models = await tester.test_models()
        print(f"利用可能なモデル: {json.dumps(models, indent=2, ensure_ascii=False)}")
        
        # Llama 3.1-latestチャットテスト
        print("\n🦙 Llama 3.1-latestチャットテスト...")
        chat_result = await tester.test_llama_chat("こんにちは！今日の天気について教えてください。")
        print(f"Llamaチャット結果: {json.dumps(chat_result, indent=2, ensure_ascii=False)}")
        
        # Llama 3.1-latestシンプルチャットテスト
        print("\n💭 Llama 3.1-latestシンプルチャットテスト...")
        simple_chat_result = await tester.test_chat("Pythonで簡単な計算機を作成してください。")
        print(f"Llamaシンプルチャット結果: {json.dumps(simple_chat_result, indent=2, ensure_ascii=False)}")
        
        # Stable Diffusion画像生成テスト
        print("\n🎨 Stable Diffusion画像生成テスト...")
        try:
            image_result = await tester.test_image_generation("美しい桜の花")
            print(f"画像生成結果: 成功 (base64データ長: {len(image_result.get('image', ''))})")
            print(f"パラメータ: {json.dumps(image_result.get('parameters', {}), indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"画像生成エラー: {e}")
        
        # Llama 3.1-latest+Stable Diffusion画像生成テスト
        print("\n🦙+🎨 Llama 3.1-latest+Stable Diffusion画像生成テスト...")
        try:
            combined_result = await tester.test_generate_with_image("美しい桜の花の画像を生成してください。画像: 桜の花")
            print(f"Llama+画像生成結果: {json.dumps(combined_result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Llama+画像生成エラー: {e}")
    
    print("\n✅ すべてのテストが完了しました！")


if __name__ == "__main__":
    asyncio.run(run_tests()) 